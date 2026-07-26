CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  action varchar(100) NOT NULL,
  target_type varchar(60) NOT NULL,
  target_id varchar(100) NOT NULL,
  changes jsonb NOT NULL DEFAULT '{}',
  ip_address varchar(64),
  user_agent varchar(500),
  correlation_id varchar(100),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_created ON audit_events(created_at);
CREATE INDEX ix_audit_target ON audit_events(target_type, target_id);
CREATE INDEX ix_audit_actor ON audit_events(actor_id, created_at);

CREATE TABLE crm_leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  name varchar(240) NOT NULL,
  email varchar(320) NOT NULL,
  phone varchar(32),
  source varchar(60) NOT NULL DEFAULT 'manual',
  stage varchar(32) NOT NULL DEFAULT 'new',
  estimated_value numeric(12,2) NOT NULL DEFAULT 0 CHECK(estimated_value >= 0),
  owner_id uuid REFERENCES customers(id) ON DELETE SET NULL,
  next_action_at timestamptz,
  created_by uuid NOT NULL REFERENCES customers(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_crm_leads_pipeline ON crm_leads(stage, next_action_at);
CREATE INDEX ix_crm_leads_owner ON crm_leads(owner_id, stage);

CREATE TABLE crm_activities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
  actor_id uuid NOT NULL REFERENCES customers(id),
  activity_type varchar(40) NOT NULL,
  summary varchar(500) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_crm_activity_lead ON crm_activities(lead_id, created_at);

CREATE TABLE crm_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
  assignee_id uuid NOT NULL REFERENCES customers(id),
  title varchar(240) NOT NULL,
  due_at timestamptz NOT NULL,
  state varchar(24) NOT NULL DEFAULT 'open',
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_crm_tasks_assignee ON crm_tasks(assignee_id, state, due_at);

CREATE TABLE marketing_campaigns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(180) NOT NULL,
  channel varchar(24) NOT NULL,
  audience_segment varchar(40) NOT NULL,
  subject varchar(180) NOT NULL,
  message varchar(1000) NOT NULL,
  call_to_action_url varchar(500) NOT NULL DEFAULT '/',
  state varchar(24) NOT NULL DEFAULT 'draft',
  scheduled_at timestamptz,
  launched_at timestamptz,
  completed_at timestamptz,
  created_by uuid NOT NULL REFERENCES customers(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_campaign_schedule ON marketing_campaigns(state, scheduled_at);

CREATE TABLE campaign_deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id uuid NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
  customer_id uuid NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  notification_id uuid REFERENCES notifications(id) ON DELETE SET NULL,
  state varchar(24) NOT NULL DEFAULT 'queued',
  created_at timestamptz NOT NULL DEFAULT now(),
  delivered_at timestamptz,
  CONSTRAINT uq_campaign_customer UNIQUE(campaign_id, customer_id)
);
CREATE INDEX ix_campaign_delivery_state ON campaign_deliveries(campaign_id, state);
