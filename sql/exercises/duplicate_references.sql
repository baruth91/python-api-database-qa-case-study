-- Expected empty: the UNIQUE constraint prevents committed duplicate references.
SELECT reference, COUNT(*) AS occurrences
FROM orders
GROUP BY reference
HAVING COUNT(*) > 1;
