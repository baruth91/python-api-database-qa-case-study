"""Database configuration shared by the teaching app and environment setup."""

import os
import re
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
DEMO_DSN = "postgresql://qa_user:qa_demo_password@127.0.0.1:55432/qa_lab"


def database_url():
    return os.environ.get("QA_DATABASE_URL", DEMO_DSN)


def connect(dsn, schema):
    if not re.fullmatch(r"qa_(?:case_[a-f0-9]{32}|demo)", schema):
        raise ValueError("Use a generated qa_case schema or the qa_demo teaching schema")
    return psycopg.connect(
        dsn,
        options=f"-c search_path={schema} -c statement_timeout=5000 -c lock_timeout=3000",
        row_factory=dict_row,
        connect_timeout=5,
    )


def initialize_schema(dsn, schema):
    # Validate before interpolating session options; identifiers use psycopg.sql.
    with connect(dsn, schema) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        conn.execute((ROOT / "sql/migrations/001_orders.sql").read_text(encoding="utf-8"))
        conn.execute((ROOT / "sql/seed.sql").read_text(encoding="utf-8"))
