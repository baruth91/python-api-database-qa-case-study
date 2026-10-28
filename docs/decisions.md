# Implementation decisions

## Keep the domain, extend the contract

The Postman case established HTTP semantics with in-memory state. This separate
repository adds a real database and a multi-item transaction so the new toolchain
addresses a new risk. Flask is a small original teaching application; Requests is
the test client. This is not a copied production framework.

## Real PostgreSQL, not SQLite

Psycopg 3 connects to PostgreSQL 18.6 in both verified environments. The project
relies on PostgreSQL constraint exceptions, transaction semantics and row locks.
An in-memory substitute would not provide evidence for that behavior.

The hosted service and Compose image use the same version and immutable image
digest. The optional Windows distribution has a separate pinned archive hash.
Its helper creates a workspace-local cluster, not a system service. Compose is
provided as another entry point; local validation used the portable distribution.

## Explicit SQL and transaction context

An ORM would be a valid real-world choice, but explicit parameterized SQL makes
the educational transaction and oracles easier to inspect here. Values use %s
parameters, never string concatenation. Generated schema identifiers use psycopg.sql.
The snapshot helper interpolates only an internal, fixed table allowlist.

The application opens a connection per request. A connection context commits on
successful exit and rolls back on an exception. Domain errors escape the context
before Flask converts them to HTTP responses. Catching a rejection inside the
context and returning normally could accidentally commit partial writes.

## Versioned baseline schema

001_orders.sql creates a new schema's tables and records schema_version = 1.
It is a reproducible initial migration, not a production migration orchestrator.
Seed SQL is separate. No TRUNCATE, database-wide reset or implicit overwrite is
needed. The manual qa_demo initializer refuses an existing schema.

The lab role owns its generated schemas for migration/teardown. It is not a model
for production least-privilege application roles; a real service should separate
runtime, migration and test-observer permissions.

## Constraints and business invariants are complementary

UNIQUE, NOT NULL, CHECK and foreign keys guard selected row/relationship rules.
The total-equals-sum invariant spans tables and is checked by application logic
and reconciliation SQL. PostgreSQL CHECK constraints are not used to query other
tables. A valid row shape can still contain an incorrect business total.

## Failure artifacts and dependency pins

requirements.in records direct choices; requirements.txt pins the resolved set
used for verification. Ruff checks style and likely Python errors; pytest executes
meaningful HTTP/database behavior. Reports are generated, ignored by Git and
uploaded in CI with finite retention. No claim of full dependency-vulnerability
auditing is made by a successful pip check.

Official references: [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html),
[PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html),
[GitHub service containers](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
