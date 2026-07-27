ALTER TABLE carts
  ADD COLUMN last_activity_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN checkout_started_at timestamptz,
  ADD COLUMN recovery_sent_at timestamptz,
  ADD COLUMN recovered_at timestamptz;

ALTER TABLE cart_items
  ADD COLUMN config_hash varchar(64);
UPDATE cart_items SET config_hash = md5(configuration::text) WHERE config_hash IS NULL;
ALTER TABLE cart_items ALTER COLUMN config_hash SET NOT NULL;
ALTER TABLE cart_items DROP CONSTRAINT IF EXISTS uq_cart_product;
ALTER TABLE cart_items
  ADD CONSTRAINT uq_cart_product_configuration UNIQUE(cart_id, product_id, config_hash);

CREATE INDEX ix_carts_recovery_due
  ON carts(state, recovery_sent_at, last_activity_at)
  WHERE state = 'active';
