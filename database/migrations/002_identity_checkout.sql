CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  woo_id integer UNIQUE,
  email varchar(320) UNIQUE NOT NULL,
  phone varchar(32),
  first_name varchar(120) NOT NULL,
  last_name varchar(120) NOT NULL DEFAULT '',
  password_hash text NOT NULL,
  role varchar(32) NOT NULL DEFAULT 'customer',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_customers_email_active ON customers(email, is_active);

CREATE TABLE refresh_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  family_id uuid NOT NULL DEFAULT gen_random_uuid(),
  token_hash varchar(64) UNIQUE NOT NULL,
  user_agent varchar(500),
  ip_address varchar(64),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);
CREATE INDEX ix_refresh_active ON refresh_sessions(customer_id, expires_at, revoked_at);
CREATE INDEX ix_refresh_family ON refresh_sessions(family_id, revoked_at);

CREATE TABLE addresses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  label varchar(80) NOT NULL DEFAULT 'Home',
  recipient_name varchar(240) NOT NULL,
  phone varchar(32) NOT NULL,
  line1 varchar(260) NOT NULL,
  line2 varchar(260),
  area varchar(160) NOT NULL,
  city varchar(120) NOT NULL DEFAULT 'Nairobi',
  delivery_notes varchar(500),
  latitude numeric(10,7),
  longitude numeric(10,7),
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_addresses_customer ON addresses(customer_id, is_default);

CREATE TABLE carts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid REFERENCES customers(id) ON DELETE CASCADE,
  guest_token_hash varchar(64) UNIQUE,
  currency varchar(3) NOT NULL DEFAULT 'KES',
  state varchar(24) NOT NULL DEFAULT 'active',
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT cart_owner CHECK (customer_id IS NOT NULL OR guest_token_hash IS NOT NULL)
);
CREATE INDEX ix_carts_customer_state ON carts(customer_id, state);

CREATE TABLE cart_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id uuid NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  product_id uuid NOT NULL REFERENCES products(id),
  quantity integer NOT NULL CHECK (quantity BETWEEN 1 AND 20),
  configuration jsonb NOT NULL DEFAULT '{}',
  added_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_cart_product UNIQUE(cart_id, product_id)
);
CREATE INDEX ix_cart_items_cart ON cart_items(cart_id);
