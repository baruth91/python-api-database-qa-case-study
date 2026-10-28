import pytest

from tests.support import running_api

pytestmark = pytest.mark.api


def test_successful_order_matches_committed_rows(api, db, request):
    response = api.create_order(
        items=[
            {"sku": "QA-NOTEBOOK", "quantity": 2},
            {"sku": "QA-PEN", "quantity": 3},
        ]
    )
    assert response.status_code == 201
    order = response.json()
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.headers["Location"] == f"/orders/{order['id']}"
    expected_total = 3496 if request.config.getoption("--wrong-total") else 3495
    assert order["totalCents"] == expected_total  # Independent: 2*1299 + 3*299.
    assert order["owner"] == "alice"
    assert order["status"] == "confirmed"
    assert order["reference"] == "order-001"
    assert order["items"] == [
        {"sku": "QA-NOTEBOOK", "quantity": 2, "unitPriceCents": 1299},
        {"sku": "QA-PEN", "quantity": 3, "unitPriceCents": 299},
    ]
    rows = db.rows(
        "SELECT o.id, o.reference, o.customer_id, o.total_cents, i.sku, i.quantity, "
        "i.unit_price_cents FROM orders o JOIN order_items i ON i.order_id = o.id "
        "WHERE o.id = %s ORDER BY i.sku",
        (order["id"],),
    )
    assert [(r["sku"], r["quantity"], r["unit_price_cents"]) for r in rows] == [
        ("QA-NOTEBOOK", 2, 1299),
        ("QA-PEN", 3, 299),
    ]
    assert all(
        str(r["id"]) == order["id"]
        and r["reference"] == "order-001"
        and r["customer_id"] == "alice"
        and r["total_cents"] == 3495
        for r in rows
    )
    assert db.rows("SELECT sku, stock FROM products ORDER BY sku") == [
        {"sku": "QA-NOTEBOOK", "stock": 8},
        {"sku": "QA-PEN", "stock": 17},
    ]
    retrieved = api.request("GET", f"/orders/{order['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == order
    assert db.exercise("reconcile_totals.sql") == []


def test_order_survives_a_new_api_instance(db, evidence):
    with running_api(db, evidence) as first:
        created = first.create_order()
        assert created.status_code == 201
        order = created.json()
    # A new Flask app and HTTP server, with the same committed PostgreSQL data.
    with running_api(db, evidence) as second:
        retrieved = second.request("GET", f"/orders/{order['id']}")
        assert retrieved.status_code == 200
        assert retrieved.json() == order
    assert len(db.rows("SELECT id FROM orders")) == 1


@pytest.mark.parametrize(
    "quantity",
    [0, -1, 1.5, "2", None, True],
    ids=["zero", "negative", "fraction", "string", "null", "boolean"],
)
def test_invalid_quantity_leaves_database_unchanged(api, db, quantity):
    before = db.snapshot()
    response = api.create_order(items=[{"sku": "QA-NOTEBOOK", "quantity": quantity}])
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "INVALID_QUANTITY"}}
    assert db.snapshot() == before


@pytest.mark.parametrize(
    "second_item, status, code",
    [
        ({"sku": "QA-PEN", "quantity": 21}, 409, "INSUFFICIENT_STOCK"),
        ({"sku": "ZZ-UNKNOWN", "quantity": 1}, 404, "PRODUCT_NOT_FOUND"),
    ],
    ids=["insufficient-second-item", "missing-second-product"],
)
def test_second_item_rejection_rolls_back_first_item(api, db, second_item, status, code):
    before = db.snapshot()
    response = api.create_order(items=[{"sku": "QA-NOTEBOOK", "quantity": 2}, second_item])
    assert response.status_code == status
    assert response.json() == {"error": {"code": code}}
    # Header and first item were inserted and stock reduced before the second item failed.
    assert db.snapshot() == before
    follow_up = api.create_order(reference="after-rollback")
    assert follow_up.status_code == 201
    assert db.rows("SELECT reference FROM orders") == [{"reference": "after-rollback"}]


def test_duplicate_reference_does_not_create_a_second_order(api, db):
    assert api.create_order().status_code == 201
    before = db.snapshot()
    duplicate = api.create_order()
    assert duplicate.status_code == 409
    assert duplicate.json() == {"error": {"code": "DUPLICATE_REFERENCE"}}
    assert db.snapshot() == before
    assert db.exercise("duplicate_references.sql") == []


def test_other_user_cannot_read_order(api, db):
    created = api.create_order()
    assert created.status_code == 201
    before = db.snapshot()
    denied = api.request("GET", f"/orders/{created.json()['id']}", user="bob")
    assert denied.status_code == 403
    assert denied.json() == {"error": {"code": "FORBIDDEN"}}
    assert api.request("GET", "/orders", user="bob").json() == {"orders": []}
    assert db.snapshot() == before


def test_anonymous_write_has_no_database_effect(api, db):
    before = db.snapshot()
    response = api.create_order(user=None)
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "UNAUTHENTICATED"}}
    assert db.snapshot() == before
