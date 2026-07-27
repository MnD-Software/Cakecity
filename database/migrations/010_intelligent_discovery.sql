CREATE TABLE discovery_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  session_hash varchar(64) NOT NULL,
  event_type varchar(40) NOT NULL,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  query varchar(240),
  context jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_discovery_customer_created
  ON discovery_events(customer_id, created_at DESC);
CREATE INDEX ix_discovery_session_created
  ON discovery_events(session_hash, created_at DESC);
CREATE INDEX ix_discovery_event_created
  ON discovery_events(event_type, created_at DESC);

CREATE INDEX ix_products_discovery_text
  ON products USING gin(
    to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(short_description, ''))
  );
