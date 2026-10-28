# An 8–10 minute demonstration

## Prepare

Install the pinned dependencies and start PostgreSQL before presenting. Keep the
contract diagram, successful-order test, rollback test and reconciliation SQL open.
Have the GitHub Actions run available for online evidence.

## Present

1. **Business risk, one minute.** “The customer receives success, but did the database
   commit the right order? What happens if the second item fails?” Compare the prior
   in-memory Postman case with this real PostgreSQL example.
2. **Data model, one minute.** Show customers, orders, items and products. Explain
   one primary key, foreign key, unique value, CHECK and nullable field.
3. **Successful order, two minutes.** Predict 3,495 cents, stocks eight/seventeen.
   Show Requests JSON, API assertions and a parameterized JOIN from a separate
   connection. Explain how this observes committed state.
4. **Rollback, two minutes.** Show the second-item rejection and before/after
   snapshots. Trace the first item's writes and where the exception leaves the
   connection context. Explain why early input rejection is a different scenario.
5. **SQL, one minute.** Show GROUP BY/HAVING reconciliation. Explain the controlled
   one-cent mutation that makes a known bad row appear in the audit result.
6. **Run and evidence, one minute.** Run python -m pytest -v. Open the successful
   Actions job and JUnit artifact. Show --wrong-total when demonstrating diagnosis;
   it is expected to fail and generates HTTP/SQL evidence.
7. **Limits, one minute.** Distinguish schema isolation, database persistence,
   API-instance restart and untested crash recovery/concurrency.

## Practice questions

- Why not run these checks against SQLite instead?
- Why does the test use a separate database connection from the API?
- Why doesn't one rollback fixture around pytest undo the HTTP server's commits?
- Which invariants are constraints, and which require business logic/reconciliation?
- Why does the audit use LEFT JOIN and COALESCE?
- Why are duplicate-reference rejection and idempotency different?
- What does a new API instance prove, and what does it not prove?
- How would you specify a concurrency test before implementing one?

Explain with the code and observed results. The goal is understanding, not a
memorized list of tools or a claim that every real project needs this architecture.
