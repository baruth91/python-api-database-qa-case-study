# Risk map and test boundaries

## Why test below the browser?

A customer can see a successful order while the backend stores incorrect items or
leaves partial stock changes after an error. HTTP checks identify consumer-visible
behavior; direct SQL establishes whether the intended committed records exist.
This case intentionally combines both layers for selected integration risks.

| Risk | Priority | Executed oracle |
| --- | --- | --- |
| Incorrect total/items stored | High | Independent 3,495-cent expectation, API body and a parameterized JOIN over header/items |
| Data only cached in the API | High | Separate database connection and retrieval through a new app/server instance |
| Partial writes on late rejection | High | Full business-table snapshots before/after failure on second item; successful follow-up request |
| Duplicate business submission | High | UNIQUE reference conflict; no extra order or stock reduction |
| Invalid data bypasses API validation | High | Five direct PostgreSQL constraint violations and unchanged state |
| Broken ownership | High | Bob cannot read Alice's order; Bob's list is empty; state stays unchanged |
| Incorrect reconciliation query | Medium | Clean orders return no anomalies; a deliberate one-cent mutation returns the exact mismatch |
| Lost NULL/missing-related-record semantics | Medium | Seeded NULL exercise and LEFT JOIN identifying Bob without an order |

Priorities are qualitative assumptions for the fictional product. They are not
measured defect rates or an assertion that every real product needs these tests.

## Isolation and reproducibility

Each pytest case receives a generated schema, migration version one and deterministic
seed data. API requests use a different PostgreSQL connection from the test's SQL
observer. Assertions therefore inspect committed state, not an uncommitted setup
transaction accidentally shared with the application.

There is no autouse transaction rollback around the entire test: that pattern would
not isolate writes committed by independent HTTP request connections. Instead,
teardown stops the API and drops only the generated schema. Fixtures are explicit;
tests remain understandable and runnable individually. Default execution is serial.

The HTTP API binds an OS-assigned loopback port. Requests has an explicit timeout;
database connections have connect, statement and lock timeouts. No sleeps, test
retries, external demo server or production dataset are required.

## Database checks versus API contracts

The direct SQL tests are deliberately coupled to the schema because their purpose
is integrity, constraints and transaction verification. Renaming a table can require
updating those oracles. A larger suite should also have black-box API contract tests
that survive internal schema changes; this slice does not justify SQL in every test.

The snapshots compare customers, products, orders and items. They are valid for this
small isolated dataset and serial execution; they are not a scalable audit strategy
for a busy shared production database.

## Failure evidence

Pytest captures request logs and produces JUnit XML. On a failing phase, a hook writes
HTTP observations; call-phase failures also get an independent committed-data snapshot.
Headers and DSNs are omitted. All bodies and rows are synthetic lab data.

The --wrong-total exercise makes one test expect 3,496 instead of 3,495. The stored
rows remain correct. This validates assertion failure propagation and evidence
collection. A separate passing test mutates a stored total and verifies the SQL audit
detects it. Those two exercises serve different purposes.

## Exclusions and next coverage

No database crash/restart recovery, parallel load, deadlock/retry policy, real
authentication provider, cross-service consistency or complete security audit is
claimed. Retrieval through a new API instance is not a crash-durability test.

Useful extensions: successful minimum/maximum quantities, missing fields, multiple
customers' orders, deliberately reordered input, and a specified concurrency case.
Concurrency must define what competing requests should observe before adding a
parallel runner. Do not equate row locking in the code with tested concurrency.
