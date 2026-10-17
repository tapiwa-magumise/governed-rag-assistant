"""Build the passage index: chunk, mask personal data, embed, store. Replaces any earlier build.

  python scripts/index.py             the whole corpus
  python scripts/index.py --limit 20  a quick trial on the first 20 passages
"""
import argparse
import hashlib
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rag import pii
from rag.aws import Bedrock, Usage
from rag.chunk import Passage, corpus_passages
from rag.db import connect

MANIFEST = ROOT / "corpus" / "manifest.json"
SEP = "\n|||\n"


def prepare(bedrock: Bedrock, p: Passage, usage: Usage) -> tuple[Passage, dict, list[float]]:
    """Mask the passage with regexes, then the ingest guardrail, then embed the masked text."""
    found: Counter = Counter()
    fields = []
    for value in (p.title, p.section, p.text):
        value, counts = pii.mask(value)
        found.update(counts)
        fields.append(value)
    # One block per passage: each block is billed in whole 1,000-character units, so three would cost more.
    g = bedrock.guard("ingest", "INPUT", [SEP.join(fields)], usage=usage)
    if g["action"] == "GUARDRAIL_INTERVENED":
        parts = g["texts"][0].split(SEP)
        if len(parts) != 3:
            raise ValueError(f"{p.id}: the guardrail changed the field separator")
        fields = parts
        for a in g["assessments"]:
            for e in a.get("sensitiveInformationPolicy", {}).get("piiEntities", []):
                found[e["type"]] += 1
    p.title, p.section, p.text = fields
    return p, dict(found), bedrock.embed(p.embed_text(), usage)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    passages = corpus_passages(ROOT / "data" / "raw", MANIFEST)[: args.limit]
    bedrock, usage = Bedrock(), Usage()
    # Each prepared passage is cached as it's done, keyed by its content, so a failed run resumes where it stopped
    # instead of paying for the guardrail and embeddings again.
    cache_file = ROOT / "data" / "index-cache.jsonl"
    cache = {}
    if cache_file.exists():
        for line in cache_file.read_text().splitlines():
            row = json.loads(line)
            cache[row["key"]] = row
    lock = threading.Lock()

    def cached(p: Passage):
        key = hashlib.sha256(json.dumps([p.id, p.title, p.section, p.text]).encode()).hexdigest()
        if key in cache:
            row = cache[key]
            p.title, p.section, p.text = row["fields"]
            return p, row["found"], row["embedding"]
        p, found, emb = prepare(bedrock, p, usage)
        with lock, cache_file.open("a") as f:
            f.write(json.dumps({"key": key, "fields": [p.title, p.section, p.text], "found": found,
                                "embedding": emb}) + "\n")
        return p, found, emb

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(cached, passages))

    masked: Counter = Counter()
    for _, found, _ in results:
        masked.update(found)
    with connect() as conn, conn.transaction():
        conn.execute("TRUNCATE passage, corpus_build RESTART IDENTITY CASCADE")
        build_id = conn.execute(
            "INSERT INTO corpus_build (manifest_sha256, documents, passages, embed_model, ingest_guardrail, masked)"
            " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (hashlib.sha256(MANIFEST.read_bytes()).hexdigest(), len({p.doc_id for p in passages}), len(passages),
             bedrock.cfg["profiles"]["embed"], json.dumps(bedrock.cfg["guardrails"]["ingest"]), json.dumps(masked)),
        ).fetchone()[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO passage (id, build_id, source, doc_id, title, section, url, updated, text, masked, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s)",
                [(p.id, build_id, p.source, p.doc_id, p.title, p.section, p.url, p.updated, p.text,
                  json.dumps(found), emb) for p, found, emb in results],
            )
    print(f"indexed {len(results)} passages from {len({p.doc_id for p in passages})} documents")
    print(f"masked: {dict(masked)}")
    print(f"embedding tokens: {usage.input_tokens:,}; cost ${usage.cost_usd:.4f}; calls {usage.calls}")


if __name__ == "__main__":
    main()
