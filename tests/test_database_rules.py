from uuid import uuid4

import psycopg
import pytest

from app.database import connect

pytestmark = pytest.mark.database


@pytest.mark.parametrize(
    "rule, exception",
    [
        ("unique-email", psycopg.errors.UniqueViolation),
        ("required-email", psycopg.errors.NotNullViolation),
        ("customer-foreign-key", psycopg.errors.ForeignKeyViolation),
        ("nonnegative-stock", psycopg.errors.CheckViolation),
        ("positive-item-quantity", psycopg.errors.CheckViolation),
    ],
)
def test_database_constraints_reject_invalid_state(db, rule, exception):
    before = db.snapshot()
    with pytest.raises(exception), connect(db.dsn, db.schema) as conn:
        if rule == "unique-email":
            conn.execute(
                "INSERT INTO customers (id, email) VALUES (%s, %s)",
                ("charlie", "alice@example.test"),
            )
        elif rule == "required-email":
            conn.execute("INSERT INTO customers (id, email) VALUES (%s, %s)", ("charlie", None))
        elif rule == "customer-foreign-key":
            conn.execute(
                "INSERT INTO orders (id, reference, customer_id, status, total_cents) "
                "VALUES (%s, %s, %s, 'confirmed', 1299)",
                (uuid4(), "foreign-key-case", "missing-customer"),
            )
        elif rule == "nonnegative-stock":
            conn.execute("UPDATE products SET stock = %s WHERE sku = %s", (-1, "QA-NOTEBOOK"))
        else:
            order_id = uuid4()
            conn.execute(
                "INSERT INTO orders (id, reference, customer_id, status, total_cents) "
                "VALUES (%s, %s, %s, 'confirmed', 0)",
                (order_id, "quantity-case", "alice"),
            )
            conn.execute(
                "INSERT INTO order_items (order_id, sku, quantity, unit_price_cents) "
                "VALUES (%s, %s, %s, %s)",
                (order_id, "QA-NOTEBOOK", 0, 1299),
            )
    # Even the parent inserted before the item constraint failure must disappear.
    assert db.snapshot() == before
    assert db.rows("SELECT version FROM schema_version") == [{"version": 1}]


def test_sql_reconciliation_accepts_consistent_orders(api, db):
    assert api.create_order(reference="first").status_code == 201
    assert (
        api.create_order(reference="second", items=[{"sku": "QA-PEN", "quantity": 3}]).status_code
        == 201
    )
    assert db.exercise("reconcile_totals.sql") == []
    assert db.exercise("duplicate_references.sql") == []


def test_sql_reconciliation_detects_a_one_cent_anomaly(api, db):
    created = api.create_order()
    assert created.status_code == 201
    with connect(db.dsn, db.schema) as conn:
        # Controlled data mutation in this test's disposable schema only.
        conn.execute(
            "UPDATE orders SET total_cents = total_cents + 1 WHERE id = %s", (created.json()["id"],)
        )
    assert db.exercise("reconcile_totals.sql") == [
        {"reference": "order-001", "total_cents": 2599, "calculated_cents": 2598},
    ]


def test_left_join_and_null_exercises_return_expected_customers(api, db):
    assert api.create_order().status_code == 201
    assert db.exercise("customers_without_orders.sql") == [
        {"id": "bob", "email": "bob@example.test"},
    ]
    assert db.exercise("missing_contact.sql") == [
        {"id": "alice", "email": "alice@example.test"},
    ]
