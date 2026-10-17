"""Every call to Bedrock goes through here, as the app's own role, in London, with its cost counted.

Settings come from Terraform's outputs: `python scripts/aws_config.py` writes them to data/aws.json. In CI they
arrive as the RAG_AWS_CONFIG environment variable, and the workflow has already assumed the role over OIDC.
"""
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ReadTimeoutError

ROOT = Path(__file__).resolve().parents[2]
REGION = "eu-west-2"

# London on-demand prices in USD, from the AWS Pricing API on 17 October 2026.
PRICE_PER_1K_TOKENS = {
    "answer": (0.000084, 0.000336),   # Nova Lite: input, output
    "judge": (0.00113, 0.00452),      # Nova Pro
    "embed": (0.0001, 0.0),           # Titan Text Embeddings v2
}
# Guardrails bill per text unit of up to 1,000 characters. The built-in personal data types are free.
PRICE_PER_TEXT_UNIT = {
    "contentPolicyUnits": 0.00015,
    "topicPolicyUnits": 0.00015,
    "contextualGroundingPolicyUnits": 0.0001,
    "sensitiveInformationPolicyUnits": 0.0001,
    "sensitiveInformationPolicyFreeUnits": 0.0,
    "wordPolicyUnits": 0.0,
}


def load_config() -> dict:
    if env := os.environ.get("RAG_AWS_CONFIG"):
        return json.loads(env)
    return json.loads((ROOT / "data" / "aws.json").read_text())


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    calls: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, kind: str, inp: int = 0, out: int = 0, cost: float = 0.0) -> None:
        with self._lock:  # shared by the indexer's threads
            self.input_tokens += inp
            self.output_tokens += out
            self.cost_usd += cost
            self.calls[kind] = self.calls.get(kind, 0) + 1


class RateLimit:
    """Spaces calls evenly across threads. Titan embeddings allow only 60 requests a minute in this account, and
    hitting the limit costs more time in backoff than waiting does."""

    def __init__(self, per_minute: float):
        self.gap, self.next, self.lock = 60.0 / per_minute, 0.0, threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next)
            self.next = start + self.gap
        time.sleep(max(0.0, start - now))


EMBED_LIMIT = RateLimit(per_minute=57)


def guardrail_cost(usage: dict) -> float:
    return sum(PRICE_PER_TEXT_UNIT.get(k, 0.0) * v for k, v in usage.items() if isinstance(v, int | float))


class Bedrock:
    def __init__(self, config: dict | None = None):
        self.cfg = config or load_config()
        retry = Config(retries={"max_attempts": 10, "mode": "adaptive"}, max_pool_connections=16, read_timeout=30)
        if os.environ.get("RAG_AWS_CONFIG"):
            session = boto3.Session(region_name=REGION)  # CI: the workflow is already the app role
        else:
            creds = boto3.client("sts").assume_role(RoleArn=self.cfg["app_role_arn"],
                                                    RoleSessionName="rag-app")["Credentials"]
            session = boto3.Session(aws_access_key_id=creds["AccessKeyId"], region_name=REGION,
                                    aws_secret_access_key=creds["SecretAccessKey"],
                                    aws_session_token=creds["SessionToken"])
        self.rt = session.client("bedrock-runtime", config=retry)

    def embed(self, text: str, usage: Usage | None = None) -> list[float]:
        # botocore retries a failed request, but not a response body that times out while being read.
        for attempt in range(5):
            EMBED_LIMIT.wait()
            try:
                r = self.rt.invoke_model(modelId=self.cfg["profiles"]["embed"],
                                         body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}))
                body = json.load(r["body"])
                break
            except ReadTimeoutError:
                if attempt == 4:
                    raise
        if usage is not None:
            n = body.get("inputTextTokenCount", 0)
            usage.add("embed", n, 0, n / 1000 * PRICE_PER_1K_TOKENS["embed"][0])
        return body["embedding"]

    def guard(self, which: str, source: str, texts: list[str], qualifiers: list[list[str]] | None = None,
              usage: Usage | None = None) -> dict:
        """Apply a guardrail. Returns the action, the (possibly masked) texts and what each policy found."""
        g = self.cfg["guardrails"][which]
        content = []
        for i, t in enumerate(texts):
            block = {"text": t}
            if qualifiers and qualifiers[i]:
                block["qualifiers"] = qualifiers[i]
            content.append({"text": block})
        r = self.rt.apply_guardrail(guardrailIdentifier=g["id"], guardrailVersion=g["version"],
                                    source=source, content=content)
        if usage is not None:
            usage.add(f"guardrail_{which}", cost=guardrail_cost(r.get("usage", {})))
        outputs = [o["text"] for o in r.get("outputs", [])]
        return {"action": r["action"], "texts": outputs if len(outputs) == len(texts) else texts,
                "outputs": outputs, "assessments": r.get("assessments", []), "usage": r.get("usage", {})}

    def converse(self, which: str, system: str, user: str, max_tokens: int = 700, temperature: float = 0.0,
                 usage: Usage | None = None) -> str:
        r = self.rt.converse(modelId=self.cfg["profiles"][which], system=[{"text": system}],
                             messages=[{"role": "user", "content": [{"text": user}]}],
                             inferenceConfig={"maxTokens": max_tokens, "temperature": temperature})
        u = r["usage"]
        if usage is not None:
            pin, pout = PRICE_PER_1K_TOKENS[which]
            usage.add(which, u["inputTokens"], u["outputTokens"],
                      u["inputTokens"] / 1000 * pin + u["outputTokens"] / 1000 * pout)
        return r["output"]["message"]["content"][0]["text"]
