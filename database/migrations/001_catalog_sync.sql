CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  woo_id integer UNIQUE NOT NULL,
  slug varchar(220) UNIQUE NOT NULL,
  name varchar(260) NOT NULL,
  description text NOT NULL DEFAULT '',
  price_kes numeric(12,2) NOT NULL CHECK (price_kes >= 0),
  regular_price_kes numeric(12,2) CHECK (regular_price_kes >= 0),
  stock_quantity integer,
  in_stock boolean NOT NULL DEFAULT true,
  status varchar(32) NOT NULL DEFAULT 'publish',
  image_url text,
  source_modified_at timestamptz,
  synchronized_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_products_browse ON products(status, in_stock);
CREATE INDEX IF NOT EXISTS ix_products_name ON products(name);

CREATE TABLE IF NOT EXISTS webhook_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id varchar(160) NOT NULL,
  delivery_key varchar(190) UNIQUE NOT NULL,
  topic varchar(80) NOT NULL,
  resource varchar(80) NOT NULL,
  payload jsonb NOT NULL,
  payload_hash varchar(64) NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'received',
  error text,
  attempts integer NOT NULL DEFAULT 0,
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_webhook_processing ON webhook_events(state, received_at);

CREATE TABLE IF NOT EXISTS sync_checkpoints (
  resource varchar(80) PRIMARY KEY,
  cursor varchar(260),
  last_success_at timestamptz,
  last_error text
);
