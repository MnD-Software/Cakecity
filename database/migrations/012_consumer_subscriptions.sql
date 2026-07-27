CREATE TABLE consumer_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  address_id uuid REFERENCES addresses(id) ON DELETE SET NULL,
  name varchar(120) NOT NULL,
  cadence varchar(20) NOT NULL CHECK (cadence IN ('once', 'weekly', 'monthly', 'quarterly', 'yearly')),
  configuration jsonb NOT NULL DEFAULT '{}',
  fulfilment varchar(20) NOT NULL CHECK (fulfilment IN ('delivery', 'pickup')),
  delivery_slot varchar(120) NOT NULL,
  state varchar(20) NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'paused', 'completed', 'cancelled')),
  next_run_at timestamptz NOT NULL,
  last_run_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_consumer_subscriptions_due
  ON consumer_subscriptions(state, next_run_at);
CREATE INDEX ix_consumer_subscriptions_customer
  ON consumer_subscriptions(customer_id, created_at DESC);

CREATE TABLE consumer_subscription_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id uuid NOT NULL REFERENCES consumer_subscriptions(id) ON DELETE CASCADE,
  scheduled_for timestamptz NOT NULL,
  state varchar(20) NOT NULL DEFAULT 'ready' CHECK (state IN ('ready', 'ordered', 'skipped')),
  order_id uuid REFERENCES orders(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_consumer_subscription_run UNIQUE(subscription_id, scheduled_for)
);
CREATE INDEX ix_consumer_subscription_runs_plan
  ON consumer_subscription_runs(subscription_id, scheduled_for DESC);
