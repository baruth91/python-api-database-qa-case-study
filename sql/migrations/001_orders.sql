-- Version 1: applied to a new, isolated schema. No destructive reset migration.
CREATE TABLE schema_version (version integer PRIMARY KEY);
INSERT INTO schema_version VALUES (1);

CREATE TABLE customers (
    id text PRIMARY KEY,
    email text NOT NULL UNIQUE,
    phone text
);

CREATE TABLE products (
    sku text PRIMARY KEY,
    unit_price_cents integer NOT NULL CHECK (unit_price_cents > 0),
    stock integer NOT NULL CHECK (stock >= 0)
);

CREATE TABLE orders (
    id uuid PRIMARY KEY,
    reference text NOT NULL UNIQUE CHECK (reference ~ '^[A-Za-z0-9_-]{1,64}$'),
    customer_id text NOT NULL REFERENCES customers(id),
    status text NOT NULL CHECK (status = 'confirmed'),
    total_cents bigint NOT NULL CHECK (total_cents >= 0),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_id uuid NOT NULL REFERENCES orders(id),
    sku text NOT NULL REFERENCES products(sku),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price_cents integer NOT NULL CHECK (unit_price_cents > 0),
    PRIMARY KEY (order_id, sku)
);
