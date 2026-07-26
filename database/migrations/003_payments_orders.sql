CREATE TABLE orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reference varchar(40) UNIQUE NOT NULL,
  woo_id integer UNIQUE,
  customer_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  customer_email varchar(320) NOT NULL,
  customer_phone varchar(32) NOT NULL,
  customer_name varchar(240) NOT NULL,
  currency varchar(3) NOT NULL DEFAULT 'KES',
  subtotal numeric(12,2) NOT NULL CHECK(subtotal >= 0),
  delivery_fee numeric(12,2) NOT NULL CHECK(delivery_fee >= 0),
  discount numeric(12,2) NOT NULL DEFAULT 0 CHECK(discount >= 0),
  total numeric(12,2) NOT NULL CHECK(total >= 0),
  fulfilment varchar(24) NOT NULL,
  delivery_slot varchar(80),
  delivery_address jsonb NOT NULL DEFAULT '{}',
  state varchar(32) NOT NULL DEFAULT 'awaiting_payment',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_orders_customer_created ON orders(customer_id, created_at);
CREATE INDEX ix_orders_state_created ON orders(state, created_at);

CREATE TABLE order_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id uuid NOT NULL REFERENCES products(id),
  woo_product_id integer NOT NULL,
  product_name varchar(260) NOT NULL,
  quantity integer NOT NULL CHECK(quantity BETWEEN 1 AND 20),
  unit_price numeric(12,2) NOT NULL CHECK(unit_price >= 0),
  line_total numeric(12,2) NOT NULL CHECK(line_total >= 0),
  configuration jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_order_lines_order ON order_lines(order_id);

CREATE TABLE payment_intents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  idempotency_key varchar(180) UNIQUE NOT NULL,
  client_secret_hash varchar(64) NOT NULL,
  method varchar(32) NOT NULL,
  provider varchar(32) NOT NULL,
  provider_reference varchar(180) UNIQUE,
  merchant_request_id varchar(180),
  amount numeric(12,2) NOT NULL CHECK(amount > 0),
  currency varchar(3) NOT NULL DEFAULT 'KES',
  state varchar(32) NOT NULL DEFAULT 'created',
  failure_code varchar(100),
  failure_message varchar(500),
  provider_payload jsonb NOT NULL DEFAULT '{}',
  paid_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_payment_order ON payment_intents(order_id);
CREATE INDEX ix_payment_state_created ON payment_intents(state, created_at);

CREATE TABLE payment_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider varchar(32) NOT NULL,
  provider_event_id varchar(190) NOT NULL,
  payload jsonb NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'received',
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  CONSTRAINT uq_payment_provider_event UNIQUE(provider, provider_event_id)
);

CREATE TABLE outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type varchar(60) NOT NULL,
  aggregate_id uuid NOT NULL,
  topic varchar(100) NOT NULL,
  payload jsonb NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_outbox_aggregate_topic UNIQUE(aggregate_id, topic)
);
CREATE INDEX ix_outbox_dispatch ON outbox_events(state, available_at);
