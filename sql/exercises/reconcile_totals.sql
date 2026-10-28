-- Return inconsistent orders, rather than trusting the API's reported total.
SELECT o.reference, o.total_cents,
       COALESCE(SUM(i.quantity * i.unit_price_cents), 0) AS calculated_cents
FROM orders AS o
LEFT JOIN order_items AS i ON i.order_id = o.id
GROUP BY o.id, o.reference, o.total_cents
HAVING o.total_cents <> COALESCE(SUM(i.quantity * i.unit_price_cents), 0)
ORDER BY o.reference;
