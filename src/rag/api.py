"""HTTP API for the web page.

  uvicorn rag.api:app --app-dir src --port 8000
"""
import json
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.answer import ask
from rag.aws import Bedrock
from rag.db import connect

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Procurement assistant", docs_url="/api/docs", openapi_url="/api/openapi.json")
_bedrock: Bedrock | None = None


def bedrock() -> Bedrock:
    global _bedrock
    if _bedrock is None:
        _bedrock = Bedrock()
    return _bedrock


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.post("/api/ask")
def ask_question(q: Question) -> dict:
    try:
        return ask(q.question, channel="web", bedrock=bedrock()).to_dict()
    except (BotoCoreError, ClientError) as e:
        # Bedrock refused or couldn't be reached. The page says so instead of failing silently.
        raise HTTPException(503, "The model service isn't available right now.") from e


def _latest(pattern: str) -> dict | None:
    runs = sorted((ROOT / "evals" / "results").glob(pattern))
    return json.loads(runs[-1].read_text()) if runs else None


@app.get("/api/evaluation")
def evaluation() -> dict:
    """The latest evaluation summary and the latest personal data check; either is null until it has run."""
    run = _latest("eval-*.json")
    return {"evaluation": run["summary"] if run else None, "personal_data": _latest("pii-*.json")}


@app.get("/api/audit")
def audit(limit: int = 25) -> list[dict]:
    """Recent log rows. Questions are stored masked, so nothing personal can come back from here."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, at, channel, question, outcome, cardinality(passage_ids), guardrail, cost_usd, latency_ms"
            " FROM audit_log ORDER BY id DESC LIMIT %s", (min(limit, 100),)).fetchall()
    keys = ("id", "at", "channel", "question", "outcome", "passages", "guardrail", "cost_usd", "latency_ms")
    return [dict(zip(keys, r)) | {"cost_usd": float(r[7])} for r in rows]


@app.get("/api/corpus")
def corpus() -> dict:
    with connect() as conn:
        build = conn.execute("SELECT built_at, documents, passages, masked FROM corpus_build ORDER BY id DESC LIMIT 1").fetchone()
        by_source = dict(conn.execute("SELECT source, count(DISTINCT doc_id) FROM passage GROUP BY source").fetchall())
    if not build:
        raise HTTPException(404, "No corpus built yet")
    return {"built_at": build[0], "documents": build[1], "passages": build[2], "masked": build[3], "by_source": by_source}


@app.get("/api/documents")
def documents() -> list[dict]:
    """Every document in the corpus, newest first, from the committed manifest: titles and dates only."""
    manifest = json.loads((ROOT / "corpus" / "manifest.json").read_text())["documents"]
    docs = [{"source": d["source"], "id": d["id"], "title": d["title"], "updated": d["updated"],
             "url": d.get("url") or f"https://www.find-tender.service.gov.uk/Notice/{d['id']}"} for d in manifest]
    return sorted(docs, key=lambda d: d["updated"], reverse=True)


# The page is one static file with no build step; mounted last so the API routes above take precedence.
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
