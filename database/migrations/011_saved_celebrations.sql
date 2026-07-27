CREATE TABLE saved_cakes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_saved_cake_customer_product UNIQUE(customer_id, product_id)
);
CREATE INDEX ix_saved_cakes_customer_created
  ON saved_cakes(customer_id, created_at DESC);

CREATE TABLE saved_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  label varchar(80) NOT NULL,
  message varchar(160) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_saved_messages_customer_created
  ON saved_messages(customer_id, created_at DESC);
