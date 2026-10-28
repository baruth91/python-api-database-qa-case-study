"""Small REST application with real PostgreSQL transactions, for QA education."""

import os
import re
from uuid import uuid4

import psycopg
from flask import Flask, g, jsonify, request

from app.database import connect, database_url


class RejectedOrder(Exception):
    def __init__(self, status, code):
        self.status = status
        self.code = code


def read_order(conn, order_id):
    row = conn.execute(
        "SELECT id, reference, customer_id, status, total_cents FROM orders WHERE id = %s",
        (order_id,),
    ).fetchone()
    if row is None:
        raise RejectedOrder(404, "ORDER_NOT_FOUND")
    items = conn.execute(
        "SELECT sku, quantity, unit_price_cents FROM order_items WHERE order_id = %s ORDER BY sku",
        (order_id,),
    ).fetchall()
    return {
        "id": str(row["id"]),
        "reference": row["reference"],
        "owner": row["customer_id"],
        "status": row["status"],
        "totalCents": row["total_cents"],
        "items": [
            {"sku": i["sku"], "quantity": i["quantity"], "unitPriceCents": i["unit_price_cents"]}
            for i in items
        ],
    }


def create_app(dsn, schema):
    app = Flask(__name__)
    tokens = {"demo-alice-token": "alice", "demo-bob-token": "bob"}

    @app.errorhandler(RejectedOrder)
    def rejection(error):
        return jsonify(error={"code": error.code}), error.status

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error={"code": "ROUTE_NOT_FOUND"}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify(error={"code": "INTERNAL_ERROR"}), 500

    @app.before_request
    def authenticate():
        if request.path == "/health":
            return
        header = request.headers.get("Authorization", "")
        g.owner = tokens.get(header[7:] if header.startswith("Bearer ") else "")
        if not g.owner:
            raise RejectedOrder(401, "UNAUTHENTICATED")

    @app.get("/health")
    def health():
        with connect(dsn, schema) as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify(status="ready")

    @app.get("/products/<sku>")
    def product(sku):
        with connect(dsn, schema) as conn:
            row = conn.execute("SELECT * FROM products WHERE sku = %s", (sku,)).fetchone()
        if row is None:
            raise RejectedOrder(404, "PRODUCT_NOT_FOUND")
        return jsonify(sku=row["sku"], unitPriceCents=row["unit_price_cents"], stock=row["stock"])

    @app.post("/orders")
    def create_order():
        if not request.is_json:
            raise RejectedOrder(415, "UNSUPPORTED_MEDIA_TYPE")
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise RejectedOrder(400, "INVALID_BODY")
        reference = body.get("reference")
        if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", reference):
            raise RejectedOrder(400, "INVALID_REFERENCE")
        items = body.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 5:
            raise RejectedOrder(400, "INVALID_ITEMS")
        seen = set()
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("sku"), str):
                raise RejectedOrder(400, "INVALID_ITEMS")
            if item["sku"] in seen:
                raise RejectedOrder(400, "DUPLICATE_PRODUCT")
            seen.add(item["sku"])
            if type(item.get("quantity")) is not int or not 1 <= item["quantity"] <= 1_000_000:
                raise RejectedOrder(400, "INVALID_QUANTITY")

        order_id = uuid4()
        try:
            # Leaving this context commits. Any propagated exception rolls it all back.
            with connect(dsn, schema) as conn:
                conn.execute(
                    "INSERT INTO orders (id, reference, customer_id, status, total_cents) "
                    "VALUES (%s, %s, %s, 'confirmed', 0)",
                    (order_id, reference, g.owner),
                )
                total = 0
                # Stable locking order reduces deadlock risk; concurrency is not claimed as tested.
                for item in sorted(items, key=lambda value: value["sku"]):
                    row = conn.execute(
                        "SELECT unit_price_cents, stock FROM products WHERE sku = %s FOR UPDATE",
                        (item["sku"],),
                    ).fetchone()
                    if row is None:
                        raise RejectedOrder(404, "PRODUCT_NOT_FOUND")
                    if item["quantity"] > row["stock"]:
                        raise RejectedOrder(409, "INSUFFICIENT_STOCK")
                    conn.execute(
                        "UPDATE products SET stock = stock - %s WHERE sku = %s",
                        (item["quantity"], item["sku"]),
                    )
                    conn.execute(
                        "INSERT INTO order_items (order_id, sku, quantity, unit_price_cents) "
                        "VALUES (%s, %s, %s, %s)",
                        (order_id, item["sku"], item["quantity"], row["unit_price_cents"]),
                    )
                    total += item["quantity"] * row["unit_price_cents"]
                conn.execute("UPDATE orders SET total_cents = %s WHERE id = %s", (total, order_id))
                result = read_order(conn, order_id)
        except psycopg.errors.UniqueViolation as error:
            if error.diag.constraint_name != "orders_reference_key":
                raise
            raise RejectedOrder(409, "DUPLICATE_REFERENCE") from error
        return jsonify(result), 201, {"Location": f"/orders/{order_id}"}

    @app.get("/orders/<uuid:order_id>")
    def order(order_id):
        with connect(dsn, schema) as conn:
            result = read_order(conn, order_id)
        if result["owner"] != g.owner:
            raise RejectedOrder(403, "FORBIDDEN")
        return jsonify(result)

    @app.get("/orders")
    def orders():
        with connect(dsn, schema) as conn:
            ids = conn.execute(
                "SELECT id FROM orders WHERE customer_id = %s ORDER BY reference", (g.owner,)
            ).fetchall()
            result = [read_order(conn, row["id"]) for row in ids]
        return jsonify(orders=result)

    return app


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    run_simple(
        "127.0.0.1",
        int(os.environ.get("PORT", "5000")),
        create_app(database_url(), "qa_demo"),
        use_reloader=False,
    )
