# Learn API and database testing through the case

## 1. Predict before running

Read the contract. Two notebooks cost 2 × 1,299 cents and three pens cost 3 × 299.
The independent total is 3,495. Starting stocks ten and twenty become eight and
seventeen. Identify where each expectation is checked in the successful-order test.

Checkpoint: explain why computing expected_total from response.totalCents would
not validate the calculation.

## 2. Trace a real HTTP request

Open tests/support.py and test_order_consistency.py. Requests sends JSON over
loopback HTTP to the running Flask server. The server opens its own Psycopg
connection, executes a transaction, commits and returns a response.

The test's Database.rows helper opens a different connection. It sees committed
rows, not the application's uncommitted transaction. This is different from a
Flask test client calling a handler without crossing an HTTP boundary.

Checkpoint: draw the path pytest → Requests → HTTP → Flask → Psycopg → PostgreSQL.
Then add the independent SQL observation from pytest to PostgreSQL.

## 3. Read a relationship with JOIN

```sql
SELECT o.reference, i.sku, i.quantity, i.unit_price_cents
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.id
WHERE o.id = %s
ORDER BY i.sku;
```

Bind the ID as a parameter, not by formatting it into the SQL string. The successful
test checks the two rows and exact independent item values. An order header alone
would not prove that both requested items were stored correctly.

Checkpoint: explain why this JOIN returns two rows for one order.

## 4. Reconcile totals with GROUP BY and HAVING

Open sql/exercises/reconcile_totals.sql. The LEFT JOIN retains an order even if its
items are missing. GROUP BY produces one result per order. SUM computes item totals;
COALESCE treats a missing aggregate as zero. HAVING selects mismatches.

The clean-data test expects no rows. The anomaly test deliberately adds one cent
to an isolated order total and expects exactly:

```text
reference: order-001
total_cents: 2599
calculated_cents: 2598
```

Checkpoint: explain why an audit query should also be tested on known bad data.
An always-empty query would incorrectly pass only the clean-data check.

## 5. Observe a late rollback

The order transaction inserts a header, reduces notebook stock and inserts the
first item. The second item requests twenty-one pens when only twenty exist.
The exception leaves the connection context and rolls back every preceding write.

```python
before = db.snapshot()
response = api.create_order(
    items=[
        {"sku": "QA-NOTEBOOK", "quantity": 2},
        {"sku": "QA-PEN", "quantity": 21},
    ]
)
assert response.status_code == 409
assert db.snapshot() == before
```

A follow-up valid order succeeds. Compare this with invalid quantity zero, which
is rejected before writes begin. Both matter, but only the late failure exercises
rollback after partial work inside the transaction.

Checkpoint: identify the connection context boundary in app/server.py and explain
what would happen if the error were swallowed inside it.

## 6. Test constraints directly

Open test_database_rules.py. The database rejects duplicate email, missing required
email, unknown customer, negative stock and zero item quantity. Tests expect the
specific Psycopg constraint exception rather than any generic error.

The invalid-item case first inserts a valid parent order in the same transaction.
When the child fails its CHECK, the parent must also disappear. The subsequent
snapshot verifies that rollback.

Checkpoint: explain why API validation and database constraints protect different
entry paths. A script, import or another service might bypass the API.

## 7. Understand NULL and missing relationships

missing_contact.sql uses IS NULL; customers_without_orders.sql uses LEFT JOIN and
filters missing order IDs. After Alice orders, Bob remains the customer without
orders, while Alice remains the customer without a phone.

duplicate_references.sql groups by reference and filters counts above one. The
UNIQUE constraint should make its result empty for committed valid data.

Checkpoint: explain why = NULL is not the same predicate as IS NULL.

## 8. Investigate the one-cent failure

Run the deliberate-failure command in the README. Inspect the JSON under
reports/failures: the HTTP total and committed database total are both 3,495;
the test deliberately expects 3,496. Classify this as a wrong test expectation.
Run the ordinary suite to restore a green result; no source mutation is needed.

Checkpoint: distinguish this failing assertion exercise from the passing SQL
anomaly-detection test. The first proves reporting; the second proves an audit oracle.

## 9. Make an independent change

Exercise A: add a successful single-pen order. Predict 299 cents, pen stock nineteen,
unchanged notebook stock and exactly one item row. Verify both API and SQL evidence.

Exercise B: add a duplicate-SKU input. The contract expects 400 DUPLICATE_PRODUCT
before any write. Verify unchanged tables, not just the error code.

Exercise C: write a query listing every customer and order count, including zero.
Use LEFT JOIN and COUNT(o.id), not COUNT(*), for Bob's zero-order row.

Exercise D: replace IS NULL with = NULL in an exercise copy. Predict why it returns
no rows even though Alice's phone is absent. Restore the correct predicate.

Suggested answers: A has total 299 and stock nineteen; B leaves the initial snapshot
unchanged; C returns Alice with one and Bob with zero after an Alice order; D uses
SQL's unknown comparison result rather than a true NULL predicate. These extensions
are not included in the baseline count until implemented and executed.

## 10. State the limits accurately

A new API instance can retrieve a committed order, but the PostgreSQL server was
not crashed or restarted. Row locking exists, but concurrent load was not tested.
Unique references reject duplicate writes, but replay does not return an idempotent
success. Explain these boundaries before proposing additional coverage.
