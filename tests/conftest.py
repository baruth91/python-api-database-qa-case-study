import json
import re
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app.database import ROOT, database_url, initialize_schema
from tests.support import Database, running_api


@pytest.fixture
def db():
    dsn = database_url()
    schema = f"qa_case_{uuid4().hex}"
    # A new schema for every test; never TRUNCATE or reset a supplied database.
    initialize_schema(dsn, schema)
    try:
        yield Database(dsn, schema)
    finally:
        # Only this fixture's generated identifier is eligible for cleanup.
        assert re.fullmatch(r"qa_case_[a-f0-9]{32}", schema)
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def evidence():
    return []


@pytest.fixture
def api(db, evidence):
    with running_api(db, evidence) as client:
        yield client


def pytest_addoption(parser):
    parser.addoption(
        "--wrong-total", action="store_true", help="Deliberate one-cent failure exercise"
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        path = ROOT / "reports/failures"
        path.mkdir(parents=True, exist_ok=True)
        details = {
            "test": item.nodeid,
            "phase": report.when,
            "http": item.funcargs.get("evidence", []),
        }
        db = item.funcargs.get("db")
        if db is not None and report.when == "call":
            try:
                details["committedDatabase"] = db.snapshot()
            except psycopg.Error:
                details["committedDatabase"] = "Unavailable; inspect captured pytest logs"
        filename = re.sub(r"[^A-Za-z0-9_-]", "_", item.nodeid)
        (path / f"{filename}.json").write_text(
            json.dumps(details, indent=2, default=str) + "\n", encoding="utf-8"
        )
