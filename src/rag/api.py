"""HTTP API for the web page.

  uvicorn rag.api:app --app-dir src --port 8000
"""
import json
from pathlib import Path

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
    return ask(q.question, channel="web", bedrock=bedrock()).to_dict()


@app.get("/api/evaluation")
def evaluation() -> dict:
    runs = sorted((ROOT / "evals" / "results").glob("eval-*.json"))
    if not runs:
        raise HTTPException(404, "No evaluation run yet")
    return json.loads(runs[-1].read_text())


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


dist = ROOT / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
