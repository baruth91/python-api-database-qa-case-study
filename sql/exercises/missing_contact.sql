-- NULL is absence of a value: use IS NULL, not = NULL.
SELECT id, email FROM customers WHERE phone IS NULL ORDER BY id;
