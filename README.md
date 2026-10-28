# API and PostgreSQL consistency with Python

[![Integration checks](https://github.com/baruth91/python-api-database-qa-case-study/actions/workflows/integration.yml/badge.svg)](https://github.com/baruth91/python-api-database-qa-case-study/actions/workflows/integration.yml)

A practical QA case study using **Requests, pytest, Psycopg and real PostgreSQL**.
An HTTP response is only part of the evidence: tests independently inspect committed
rows, related records, stock and transaction rollback.

This original educational project is part of Phillip Baruth's QA community material
and learning-in-public portfolio. It builds on the [Postman order case](https://github.com/baruth91/postman-api-qa-case-study),
extending the domain to multiple items and database persistence. It is a small
teaching application with synthetic data, not a production commerce platform.

## Start here

Prerequisites: **Python 3.13** and a disposable **PostgreSQL 18.6** database. The
verified Python patch is in `.python-version`. Docker Compose is one convenient
database option; a portable Windows alternative is provided below.

```sh
git clone https://github.com/baruth91/python-api-database-qa-case-study.git
cd python-api-database-qa-case-study
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```sh
# Linux/macOS
source .venv/bin/activate
```

Then install and run:

```sh
python -m pip install -r requirements.txt
docker compose up -d --wait
python -m pytest -v
docker compose down --volumes
```

The default DSN is `postgresql://qa_user:qa_demo_password@127.0.0.1:55432/qa_lab`.
These are public lab credentials. Compose binds the port only to loopback and has
no persistent named volume. The image is pinned by version **and digest**.

For another dedicated lab database, set `QA_DATABASE_URL`. For example:

```powershell
$env:QA_DATABASE_URL = 'postgresql://qa_user:qa_demo_password@127.0.0.1:55432/qa_lab'
```

```sh
export QA_DATABASE_URL='postgresql://qa_user:qa_demo_password@127.0.0.1:55432/qa_lab'
```

The account needs permission to create schemas. Each test creates a generated
`qa_case_<uuid>` schema, applies migration/seed SQL, starts its own API when needed,
and drops **only its generated schema** during teardown. Existing schemas are not
reset. Use synthetic data in a dedicated lab database.

## Windows without Docker

From the activated environment:

```powershell
python scripts/windows_postgres.py prepare
python scripts/windows_postgres.py start
python -m pytest -v
python scripts/windows_postgres.py stop
```

The optional helper downloads the PostgreSQL 18.6 EDB binary archive referenced by
the PostgreSQL Windows download page and verifies a pinned SHA-256 before extraction.
Binaries and cluster data stay in ignored `.tools/` and `.work/` directories.
It installs no Windows service, uses SCRAM authentication and listens on loopback
port 55432. Start reuses that local cluster; test schemas are still new each time.
Do not start Compose and the portable server on the same port simultaneously.

## What the 21 cases demonstrate

| Coverage | Evidence |
| --- | --- |
| Successful multi-item order | HTTP body and headers, joined committed rows, exact total 3,495 cents and both stock changes |
| Persistence across API instances | A new Flask app and HTTP server retrieves the same committed order |
| Six invalid quantity types/values | 400 response and all four business tables unchanged |
| Two late transaction rejections | Second item fails after first-item writes; header, items and stock all roll back |
| Duplicate order reference | 409 and no second write; uniqueness is not an idempotent replay contract |
| Access control | Another user's read is denied; anonymous creation leaves no database changes |
| Five database constraints | UNIQUE, NOT NULL, foreign key and two CHECK examples reject invalid state |
| Three SQL exercises | Clean reconciliation, detection of a one-cent anomaly, LEFT JOIN and NULL handling |

The cases consist of 13 API integration cases and eight database/SQL cases. Some
SQL cases create data through HTTP, but their main purpose is a database oracle.
No SQLite substitution, API mock, retry or fixed sleep is used.

## Run online

Open [Actions → API and PostgreSQL case checks](https://github.com/baruth91/python-api-database-qa-case-study/actions/workflows/integration.yml),
then **Run workflow → main → Run workflow**. The Ubuntu runner starts its own
PostgreSQL service container, checks code and runs the suite. Repository permissions
are required to trigger it; learners can fork and enable Actions.

JUnit XML is uploaded as `api-postgresql-evidence`. On failure, JSON files include
the observed HTTP responses and committed database snapshot, without authorization
headers or the DSN. Artifacts expire after seven days; the validation document
links durable workflow outcomes.

## Study and demonstrate

- [Risk map and scope](docs/test-strategy.md)
- [API contract and data model](docs/api-contract.md)
- [Guided tutorial and SQL exercises](docs/tutorial.md)
- [An 8–10 minute demonstration](docs/demo.md)
- [Execution evidence](docs/validation.md)
- [Architecture decisions](docs/decisions.md)

For a controlled assertion failure:

```sh
python -m pytest tests/test_order_consistency.py::test_successful_order_matches_committed_rows --wrong-total --junitxml=reports/deliberate-failure.xml
```

Expect **one failed test and exit code 1**. The exercise expects 3,496 cents while
the correct response contains 3,495; inspect `reports/failures/`. A normal
`python -m pytest -v` uses the correct expectation. Separately, a passing SQL test
intentionally changes one stored total and proves that reconciliation detects it.

## Explore manually

With PostgreSQL running, initialize a separate manual-demo schema once:

```sh
python -m app.manage
python -m app.server
```

The API listens at `http://127.0.0.1:5000`. Import no existing Postman collection
unchanged: this contract adds a `reference` and an `items` array. Example body:

```json
{"reference":"manual-001","items":[{"sku":"QA-NOTEBOOK","quantity":2}]}
```

Send `POST /orders` with JSON content type and
`Authorization: Bearer demo-alice-token`. Manual state remains in `qa_demo` until
the disposable database is removed. Initialization refuses to overwrite that
schema; automated tests remain independent from it.

## Limits and references

The project verifies commits, rollback and retrieval across API instances. It does
not test database crash recovery, distributed transactions, concurrent load, real
identity providers, complete API/security coverage or production deployment. SQL
oracles intentionally couple selected integration tests to the schema; ordinary
API contract tests need not all query database internals.

- [Psycopg transaction contexts](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [GitHub Actions PostgreSQL services](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
- [PostgreSQL Windows distributions](https://www.postgresql.org/download/windows/)

Original project material is MIT licensed. Third-party dependencies and PostgreSQL
retain their own licenses.
