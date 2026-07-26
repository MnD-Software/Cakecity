CREATE TABLE loyalty_accounts (
  customer_id uuid PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  points_balance integer NOT NULL DEFAULT 0 CHECK(points_balance >= 0),
  lifetime_points integer NOT NULL DEFAULT 0 CHECK(lifetime_points >= 0),
  lifetime_spend numeric(14,2) NOT NULL DEFAULT 0 CHECK(lifetime_spend >= 0),
  tier varchar(24) NOT NULL DEFAULT 'silver',
  status varchar(24) NOT NULL DEFAULT 'active',
  joined_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE loyalty_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id uuid REFERENCES orders(id) ON DELETE SET NULL,
  entry_type varchar(40) NOT NULL,
  points integer NOT NULL,
  balance_after integer NOT NULL CHECK(balance_after >= 0),
  source_key varchar(190) UNIQUE NOT NULL,
  description varchar(300) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_loyalty_ledger_customer ON loyalty_ledger(customer_id, created_at);
CREATE TABLE wallet_accounts (
  customer_id uuid PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  balance numeric(12,2) NOT NULL DEFAULT 0 CHECK(balance >= 0),
  currency varchar(3) NOT NULL DEFAULT 'KES',
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wallet_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id uuid REFERENCES orders(id) ON DELETE SET NULL,
  entry_type varchar(40) NOT NULL,
  amount numeric(12,2) NOT NULL,
  balance_after numeric(12,2) NOT NULL CHECK(balance_after >= 0),
  source_key varchar(190) UNIQUE NOT NULL,
  description varchar(300) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_wallet_ledger_customer ON wallet_ledger(customer_id, created_at);
CREATE TABLE referral_codes (
  customer_id uuid PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  code varchar(20) UNIQUE NOT NULL,
  uses integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE referrals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  referred_id uuid UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  code varchar(20) NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'pending',
  qualifying_order_id uuid REFERENCES orders(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
CREATE INDEX ix_referrals_referrer ON referrals(referrer_id, state);
CREATE TABLE celebration_moments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  name varchar(160) NOT NULL,
  relationship varchar(80) NOT NULL,
  occasion varchar(40) NOT NULL,
  event_date date NOT NULL,
  reminder_days jsonb NOT NULL DEFAULT '[30,7,1]',
  notes varchar(500),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_moments_customer ON celebration_moments(customer_id, is_active);
CREATE UNIQUE INDEX uq_moments_self_birthday ON celebration_moments(customer_id)
  WHERE occasion = 'birthday' AND lower(relationship) = 'self';
CREATE TABLE reminder_deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  moment_id uuid NOT NULL REFERENCES celebration_moments(id) ON DELETE CASCADE,
  event_year integer NOT NULL,
  days_before integer NOT NULL,
  notification_id uuid NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
  sent_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_reminder_delivery UNIQUE(moment_id, event_year, days_before)
);
