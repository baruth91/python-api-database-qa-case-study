# Execution evidence

## Observed baseline

| Environment | Scope | Result |
| --- | --- | --- |
| Windows, Python 3.13.15, PostgreSQL 18.6 portable | 21 real HTTP/database cases | Final baseline passed: 21 passed in 17.18 seconds; Ruff and pip check passed |
| Ubuntu 24.04, Python 3.13.15, pinned PostgreSQL 18.6 image | Same suite and Ruff checks | Pending first published run |

The suite has 13 API cases and eight database/SQL cases, including parameterized
inputs. All cases use a new generated schema. Windows PostgreSQL was prepared from
the EDB archive with pinned SHA-256; Compose is supplied but was not used locally.

## Controlled failure and artifact check

The --wrong-total exercise ran the successful-order test with an expected amount
of 3,496 cents. It failed once with actual 3,495 and returned exit code 1 in 0.96
seconds. Its JSON artifact contained the HTTP exchange and four committed business
tables; the stored order total was also 3,495. No DSN was included in that artifact.

An independent PostgreSQL query confirmed version 18.6 and zero remaining
qa_case schemas after the initial suite and failure exercise. The passing SQL
anomaly case also verified detection of a deliberately altered one-cent total.

## Reproduce

Follow the README to start a disposable PostgreSQL database, then install
requirements.txt and run python -m pytest -v. Run python -m ruff check . and
python -m ruff format --check . for static checks. pip check verifies dependency
compatibility; it is not a vulnerability audit.

Runtime reports are ignored by Git. Hosted JUnit/failure artifacts are retained
for seven days. These results do not establish crash recovery, concurrency,
production security, complete coverage or production deployment readiness.
