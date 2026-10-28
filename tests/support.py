"""HTTP client and independent SQL observations for the QA examples."""

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

import requests
from werkzeug.serving import make_server

from app.database import ROOT, connect
from app.server import create_app


@dataclass
class Database:
    dsn: str = field(repr=False)
    schema: str

    def rows(self, query, params=()):
        # A separate connection observes only committed application state.
        with connect(self.dsn, self.schema) as conn:
            return conn.execute(query, params).fetchall()

    def snapshot(self):
        return {
            table: self.rows(f"SELECT * FROM {table} ORDER BY 1, 2")
            for table in ("customers", "products", "orders", "order_items")
        }

    def exercise(self, filename):
        return self.rows((ROOT / "sql/exercises" / filename).read_text(encoding="utf-8"))


class ApiClient:
    def __init__(self, url, evidence):
        self.url = url
        self.evidence = evidence
        self.session = requests.Session()
        self.session.trust_env = False  # Local lab requests must not use a machine's HTTP proxy.

    def request(self, method, path, *, user="alice", **kwargs):
        headers = kwargs.pop("headers", {})
        if user is not None:
            headers["Authorization"] = f"Bearer demo-{user}-token"
        response = self.session.request(
            method, self.url + path, headers=headers, timeout=10, **kwargs
        )
        self.evidence.append(
            {
                "method": method,
                "path": path,
                "status": response.status_code,
                "requestBody": kwargs.get("json"),
                "responseBody": response.text,
            }
        )
        return response

    def create_order(self, reference="order-001", items=None, **kwargs):
        if items is None:
            items = [{"sku": "QA-NOTEBOOK", "quantity": 2}]
        return self.request(
            "POST", "/orders", json={"reference": reference, "items": items}, **kwargs
        )


@contextmanager
def running_api(db, evidence):
    server = make_server("127.0.0.1", 0, create_app(db.dsn, db.schema), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = ApiClient(f"http://127.0.0.1:{server.server_port}", evidence)
    try:
        yield client
    finally:
        client.session.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("Teaching API did not stop")
