"""Download the corpus: the Procurement Act guidance, the current policy notes and a month of tender notices.

Raw files go to data/raw/, which git ignores: tender notices contain personal data. corpus/manifest.json
records every document with its last-updated date and a checksum, so a rebuild can be compared with this one.

  python scripts/extract.py            download, then compare with the committed manifest
  python scripts/extract.py --write    download and replace the manifest
"""
import argparse
import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "corpus" / "manifest.json"
GOVUK = "https://www.gov.uk/api/content"
FTS = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
GUIDANCE = "/government/collections/procurement-act-2023-guidance-documents"
PPNS = "/government/collections/procurement-policy-notes"
PPN_GROUP = "Procurement Act 2023 PPNs"  # the notes for the 2015 regulations and the out-of-date ones are left out
NOTICE_WINDOW = ("2026-09-01T00:00:00", "2026-10-01T00:00:00")
TLS = ssl.create_default_context(cafile=certifi.where())


def get_json(url: str) -> dict:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "governed-rag-assistant (portfolio project)"})
            with urllib.request.urlopen(req, timeout=60, context=TLS) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def publications() -> list[tuple[str, str]]:
    """(collection, publication path) for the four guidance phases and the current policy notes."""
    guidance = get_json(GOVUK + GUIDANCE)
    out = [("guidance", d["base_path"]) for d in guidance["links"]["documents"]]
    ppns = get_json(GOVUK + PPNS)
    group = next(g for g in ppns["details"]["collection_groups"] if g["title"] == PPN_GROUP)
    by_id = {d["content_id"]: d["base_path"] for d in ppns["links"]["documents"]}
    out += [("ppn", by_id[i]) for i in group["documents"]]
    return out


def govuk_documents() -> list[dict]:
    docs = []
    for collection, path in publications():
        pub = get_json(GOVUK + path)
        time.sleep(0.2)
        for att in pub["details"].get("attachments", []):
            if att.get("attachment_type") != "html":
                continue  # the PDF and ODT attachments are copies of the HTML ones
            att_path = att["url"].removeprefix("https://www.gov.uk")
            doc = get_json(GOVUK + att_path)
            time.sleep(0.2)
            out = RAW / "govuk" / (att_path.strip("/").replace("/", "__") + ".json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, indent=1))
            docs.append({"source": collection, "id": att_path, "title": doc["title"],
                         "publication": pub["title"], "updated": doc.get("public_updated_at"),
                         "url": "https://www.gov.uk" + att_path, "sha256": sha(doc["details"].get("body", ""))})
    return docs


def notices() -> list[dict]:
    url = f"{FTS}?stages=tender&limit=100&updatedFrom={NOTICE_WINDOW[0]}&updatedTo={NOTICE_WINDOW[1]}"
    docs = []
    while url:
        page = get_json(url)
        for release in page["releases"]:
            out = RAW / "notices" / (release["id"].replace("/", "_") + ".json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(release, indent=1))
            # Only the id, title and checksum are recorded: the notice itself holds contact details.
            docs.append({"source": "notice", "id": release["id"], "title": release["tender"].get("title", ""),
                         "updated": release.get("date"), "sha256": sha(release)})
        url = page.get("links", {}).get("next")
        time.sleep(0.5)
    return docs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="replace corpus/manifest.json with this download")
    args = ap.parse_args()
    docs = govuk_documents() + notices()
    docs.sort(key=lambda d: (d["source"], d["id"]))
    counts = {s: sum(d["source"] == s for d in docs) for s in ("guidance", "ppn", "notice")}
    print(f"downloaded {counts}")
    if args.write or not MANIFEST.exists():
        MANIFEST.parent.mkdir(exist_ok=True)
        MANIFEST.write_text(json.dumps({"notice_window": NOTICE_WINDOW, "documents": docs}, indent=1) + "\n")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
        return
    old = {(d["source"], d["id"]): d for d in json.loads(MANIFEST.read_text())["documents"]}
    new = {(d["source"], d["id"]): d for d in docs}
    added, removed = new.keys() - old.keys(), old.keys() - new.keys()
    changed = [k for k in new.keys() & old.keys() if new[k]["sha256"] != old[k]["sha256"]]
    for label, keys in (("added", added), ("removed", removed), ("changed", changed)):
        for k in sorted(keys):
            print(f"{label}: {k[0]} {k[1]}")
    print("matches the manifest" if not (added or removed or changed) else "differs from the manifest")


if __name__ == "__main__":
    main()
