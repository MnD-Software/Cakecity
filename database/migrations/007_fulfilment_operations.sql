CREATE TABLE ingredients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(180) UNIQUE NOT NULL,
  unit varchar(30) NOT NULL,
  stock_on_hand numeric(12,3) NOT NULL DEFAULT 0 CHECK(stock_on_hand >= 0),
  reorder_level numeric(12,3) NOT NULL DEFAULT 0 CHECK(reorder_level >= 0),
  is_active boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_ingredients_alert ON ingredients(is_active, stock_on_hand, reorder_level);
CREATE TABLE recipes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid UNIQUE NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name varchar(220) NOT NULL,
  yield_description varchar(120) NOT NULL,
  preparation_minutes integer NOT NULL DEFAULT 60 CHECK(preparation_minutes > 0),
  instructions jsonb NOT NULL DEFAULT '[]',
  allergens jsonb NOT NULL DEFAULT '[]',
  version integer NOT NULL DEFAULT 1,
  is_active boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE recipe_ingredients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id uuid NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  ingredient_id uuid NOT NULL REFERENCES ingredients(id),
  quantity numeric(12,3) NOT NULL CHECK(quantity > 0),
  CONSTRAINT uq_recipe_ingredient UNIQUE(recipe_id, ingredient_id)
);
CREATE TABLE production_tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid UNIQUE NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  state varchar(40) NOT NULL DEFAULT 'confirmed',
  priority integer NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
  assigned_to uuid REFERENCES customers(id) ON DELETE SET NULL,
  recipe_snapshot jsonb NOT NULL DEFAULT '{}',
  checklist jsonb NOT NULL DEFAULT '{}',
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_production_queue ON production_tickets(state, priority, created_at);
CREATE TABLE inventory_consumptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id uuid NOT NULL REFERENCES production_tickets(id) ON DELETE CASCADE,
  ingredient_id uuid NOT NULL REFERENCES ingredients(id),
  quantity numeric(12,3) NOT NULL CHECK(quantity > 0),
  recorded_by uuid NOT NULL REFERENCES customers(id),
  idempotency_key varchar(180) UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_consumption_ticket ON inventory_consumptions(ticket_id, created_at);
CREATE TABLE order_stage_commands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  requested_stage varchar(40) NOT NULL,
  source varchar(30) NOT NULL,
  actor_id uuid NOT NULL REFERENCES customers(id),
  idempotency_key varchar(180) UNIQUE NOT NULL,
  command_metadata jsonb NOT NULL DEFAULT '{}',
  state varchar(24) NOT NULL DEFAULT 'pending',
  failure_message varchar(500),
  created_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);
CREATE INDEX ix_stage_commands_order ON order_stage_commands(order_id, created_at);
CREATE TABLE driver_profiles (
  customer_id uuid PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  vehicle_type varchar(60) NOT NULL,
  vehicle_registration varchar(40) NOT NULL,
  is_available boolean NOT NULL DEFAULT true,
  last_seen_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE delivery_assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id uuid UNIQUE NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  driver_id uuid NOT NULL REFERENCES customers(id),
  state varchar(32) NOT NULL DEFAULT 'assigned',
  delivery_otp_hash varchar(64) NOT NULL,
  otp_expires_at timestamptz NOT NULL,
  otp_attempts integer NOT NULL DEFAULT 0 CHECK(otp_attempts <= 10),
  estimated_arrival_at timestamptz,
  accepted_at timestamptz,
  picked_up_at timestamptz,
  delivered_at timestamptz,
  proof_photo_url text,
  signature_url text,
  recipient_name varchar(180),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_delivery_driver_state ON delivery_assignments(driver_id, state, created_at);
CREATE TABLE driver_locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES delivery_assignments(id) ON DELETE CASCADE,
  latitude numeric(10,7) NOT NULL CHECK(latitude BETWEEN -90 AND 90),
  longitude numeric(10,7) NOT NULL CHECK(longitude BETWEEN -180 AND 180),
  accuracy_meters numeric(8,2),
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_driver_location_latest ON driver_locations(assignment_id, recorded_at);
CREATE TABLE delivery_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES delivery_assignments(id) ON DELETE CASCADE,
  sender_id uuid NOT NULL REFERENCES customers(id),
  sender_role varchar(24) NOT NULL,
  body varchar(500) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_delivery_messages_assignment ON delivery_messages(assignment_id, created_at);
