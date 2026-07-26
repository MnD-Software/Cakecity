CREATE TABLE corporate_accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name varchar(240) NOT NULL,
  slug varchar(180) UNIQUE NOT NULL, billing_email varchar(320) NOT NULL, phone varchar(32),
  tax_pin varchar(40), billing_address jsonb NOT NULL DEFAULT '{}',
  credit_limit numeric(14,2) NOT NULL DEFAULT 0 CHECK(credit_limit >= 0),
  approval_threshold numeric(14,2) NOT NULL DEFAULT 0 CHECK(approval_threshold >= 0),
  payment_terms_days integer NOT NULL DEFAULT 30 CHECK(payment_terms_days BETWEEN 0 AND 120),
  state varchar(24) NOT NULL DEFAULT 'active',
  account_manager_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_corporate_accounts_state ON corporate_accounts(state, name);

CREATE TABLE corporate_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES corporate_accounts(id) ON DELETE CASCADE,
  customer_id uuid UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  role varchar(24) NOT NULL DEFAULT 'requester' CHECK(role IN ('requester','approver','admin')),
  spend_limit numeric(14,2) CHECK(spend_limit IS NULL OR spend_limit >= 0),
  cost_center varchar(120), is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_corporate_member UNIQUE(account_id, customer_id)
);
CREATE INDEX ix_corporate_member_customer ON corporate_members(customer_id, is_active);

CREATE TABLE corporate_recurring_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES corporate_accounts(id) ON DELETE CASCADE,
  owner_id uuid NOT NULL REFERENCES customers(id), name varchar(180) NOT NULL,
  cadence varchar(24) NOT NULL CHECK(cadence IN ('weekly','monthly')),
  order_payload jsonb NOT NULL, next_run_at timestamptz NOT NULL,
  is_active boolean NOT NULL DEFAULT true, last_run_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_corporate_recurring_due ON corporate_recurring_orders(is_active, next_run_at);

CREATE TABLE corporate_order_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES corporate_accounts(id) ON DELETE CASCADE,
  requester_id uuid NOT NULL REFERENCES customers(id),
  order_id uuid UNIQUE REFERENCES orders(id) ON DELETE SET NULL,
  recurring_order_id uuid REFERENCES corporate_recurring_orders(id) ON DELETE SET NULL,
  reference varchar(40) UNIQUE NOT NULL, idempotency_key varchar(180) UNIQUE NOT NULL,
  purchase_order_number varchar(100), cost_center varchar(120),
  fulfilment varchar(24) NOT NULL CHECK(fulfilment IN ('delivery','pickup')),
  delivery_slot varchar(80), delivery_address jsonb NOT NULL DEFAULT '{}',
  quote_snapshot jsonb NOT NULL, subtotal numeric(14,2) NOT NULL,
  delivery_fee numeric(14,2) NOT NULL, total numeric(14,2) NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'pending_approval'
    CHECK(state IN ('pending_approval','approved','rejected','converted','cancelled')),
  rejection_reason varchar(500), submitted_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz, converted_at timestamptz
);
CREATE INDEX ix_corporate_request_queue ON corporate_order_requests(account_id, state, submitted_at);
CREATE INDEX ix_corporate_request_requester ON corporate_order_requests(requester_id, submitted_at);

CREATE TABLE corporate_approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid NOT NULL REFERENCES corporate_order_requests(id) ON DELETE CASCADE,
  actor_id uuid NOT NULL REFERENCES customers(id),
  decision varchar(24) NOT NULL CHECK(decision IN ('approved','rejected')),
  note varchar(500), decided_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_corporate_approval_request ON corporate_approvals(request_id, decided_at);

CREATE TABLE corporate_invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id uuid NOT NULL REFERENCES corporate_accounts(id) ON DELETE CASCADE,
  request_id uuid UNIQUE NOT NULL REFERENCES corporate_order_requests(id),
  order_id uuid UNIQUE NOT NULL REFERENCES orders(id),
  invoice_number varchar(50) UNIQUE NOT NULL, purchase_order_number varchar(100),
  amount numeric(14,2) NOT NULL CHECK(amount >= 0),
  amount_paid numeric(14,2) NOT NULL DEFAULT 0 CHECK(amount_paid >= 0),
  state varchar(24) NOT NULL DEFAULT 'open' CHECK(state IN ('open','part_paid','paid','overdue','void')),
  issued_at timestamptz NOT NULL DEFAULT now(), due_at timestamptz NOT NULL, paid_at timestamptz
);
CREATE INDEX ix_corporate_invoice_account ON corporate_invoices(account_id, state, due_at);

CREATE TABLE corporate_invoice_payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL REFERENCES corporate_invoices(id) ON DELETE CASCADE,
  amount numeric(14,2) NOT NULL CHECK(amount > 0),
  reference varchar(180) UNIQUE NOT NULL,
  recorded_by uuid NOT NULL REFERENCES customers(id),
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_corporate_invoice_payment ON corporate_invoice_payments(invoice_id, recorded_at);
