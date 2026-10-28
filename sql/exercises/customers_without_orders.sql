-- LEFT JOIN retains customers for whom there is no related order.
SELECT c.id, c.email
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.id
WHERE o.id IS NULL
ORDER BY c.id;
