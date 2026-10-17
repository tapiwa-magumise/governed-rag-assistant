import os

import psycopg
from pgvector.psycopg import register_vector

DSN = os.environ.get("RAG_DB", "postgresql://rag:rag-local-only@127.0.0.1:5433/rag")


def connect() -> psycopg.Connection:
    conn = psycopg.connect(DSN, autocommit=True)
    register_vector(conn)
    return conn
