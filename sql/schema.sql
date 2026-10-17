CREATE EXTENSION IF NOT EXISTS vector;

-- One row per corpus build (N8): what went in, and with which guardrail and model.
CREATE TABLE IF NOT EXISTS corpus_build (
    id              serial PRIMARY KEY,
    built_at        timestamptz NOT NULL DEFAULT now(),
    manifest_sha256 text NOT NULL,
    documents       int NOT NULL,
    passages        int NOT NULL,
    embed_model     text NOT NULL,
    ingest_guardrail text NOT NULL,
    masked          jsonb NOT NULL         -- personal data masked, by entity type
);

-- Passages hold only masked text (N1). The embedding is of the masked text too.
CREATE TABLE IF NOT EXISTS passage (
    id         text PRIMARY KEY,
    build_id   int NOT NULL REFERENCES corpus_build(id),
    source     text NOT NULL CHECK (source IN ('guidance', 'ppn', 'notice')),
    doc_id     text NOT NULL,
    title      text NOT NULL,
    section    text NOT NULL,
    url        text NOT NULL,
    updated    timestamptz,
    text       text NOT NULL,
    masked     jsonb NOT NULL DEFAULT '{}',
    embedding  vector(1024) NOT NULL,
    tsv        tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || section || ' ' || text)) STORED
);
CREATE INDEX IF NOT EXISTS passage_embedding ON passage USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS passage_tsv ON passage USING gin (tsv);

-- Every question and answer (N7). The question is stored only after the guardrail has masked it.
CREATE TABLE IF NOT EXISTS audit_log (
    id             bigserial PRIMARY KEY,
    at             timestamptz NOT NULL DEFAULT now(),
    channel        text NOT NULL,          -- web, api or an evaluation run's name
    question       text NOT NULL,          -- masked
    outcome        text NOT NULL CHECK (outcome IN ('answered', 'no_answer', 'blocked_input', 'blocked_output', 'error')),
    answer         text,
    passage_ids    text[] NOT NULL DEFAULT '{}',
    scores         real[] NOT NULL DEFAULT '{}',
    model          text,
    guardrail      jsonb NOT NULL DEFAULT '{}',   -- what each guardrail check did
    input_tokens   int NOT NULL DEFAULT 0,
    output_tokens  int NOT NULL DEFAULT 0,
    cost_usd       numeric(12, 8) NOT NULL DEFAULT 0,
    latency_ms     int NOT NULL DEFAULT 0
);
