CREATE TABLE order_timeline_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  stage varchar(40) NOT NULL,
  title varchar(180) NOT NULL,
  detail varchar(500) NOT NULL DEFAULT '',
  source varchar(40) NOT NULL,
  source_event_key varchar(190) NOT NULL,
  event_metadata jsonb NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_order_timeline_source UNIQUE(order_id, source_event_key)
);
CREATE INDEX ix_order_timeline_order ON order_timeline_events(order_id, occurred_at);

CREATE TABLE notification_preferences (
  customer_id uuid PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  in_app boolean NOT NULL DEFAULT true,
  email boolean NOT NULL DEFAULT true,
  push boolean NOT NULL DEFAULT false,
  sms boolean NOT NULL DEFAULT false,
  whatsapp boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id uuid REFERENCES orders(id) ON DELETE CASCADE,
  kind varchar(60) NOT NULL,
  title varchar(180) NOT NULL,
  body varchar(500) NOT NULL,
  data jsonb NOT NULL DEFAULT '{}',
  read_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_notifications_customer ON notifications(customer_id, created_at);

CREATE TABLE push_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  endpoint text UNIQUE NOT NULL,
  p256dh text NOT NULL,
  auth text NOT NULL,
  user_agent varchar(500),
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_push_customer_active ON push_subscriptions(customer_id, revoked_at);
