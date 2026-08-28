-- Monti Makes It — database schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customers (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ref           TEXT UNIQUE NOT NULL,
  company_name  TEXT NOT NULL,
  contact_name  TEXT,
  email         TEXT NOT NULL,
  phone         TEXT,
  website       TEXT,
  country       TEXT,
  address       TEXT,
  city          TEXT,
  state         TEXT,
  postal_code   TEXT,
  stage         TEXT NOT NULL DEFAULT 'LEAD',      -- LEAD|QUOTING|NEGOTIATING|ACTIVE|DORMANT|LOST
  membership_status TEXT NOT NULL DEFAULT 'PROSPECT',
  -- PROSPECT (quoted, never applied) | APPLIED | INTERVIEW | MEMBER | DECLINED | PAUSED
  member_since  TEXT,
  quote_limit   INTEGER NOT NULL DEFAULT 10,       -- new quotes allowed per cycle
  quote_cycle_days INTEGER NOT NULL DEFAULT 30,
  membership_note TEXT,                            -- why the limit was raised, etc.
  catalog_tags  TEXT,                              -- comma separated; grants catalog items
  freight_waived_default INTEGER NOT NULL DEFAULT 0, -- owner absorbs freight for this account
  source        TEXT,                              -- WEBSITE|REFERRAL|OUTBOUND|TRADE_SHOW|OTHER
  owner         TEXT,                              -- admin name responsible
  tags          TEXT,                              -- comma separated
  lifetime_value_cents INTEGER NOT NULL DEFAULT 0,
  notes         TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_stage ON customers(stage);

CREATE TABLE IF NOT EXISTS applications (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ref             TEXT UNIQUE NOT NULL,
  customer_id     INTEGER REFERENCES customers(id) ON DELETE SET NULL,
  company_name    TEXT NOT NULL,
  contact_name    TEXT NOT NULL,
  email           TEXT NOT NULL,
  phone           TEXT,
  website         TEXT,
  country         TEXT,
  business_type   TEXT,      -- brand, retailer, distributor, agency, startup...
  years_trading   TEXT,
  what_they_sell  TEXT,
  categories      TEXT,
  annual_volume   TEXT,      -- self-reported band
  current_manufacturer TEXT,
  why             TEXT,      -- why they want to partner
  goals           TEXT,      -- what they want to build with us
  availability    TEXT,      -- when they can take the call
  referral        TEXT,
  status          TEXT NOT NULL DEFAULT 'SUBMITTED',
  -- SUBMITTED | SCREENING | INTERVIEW_SCHEDULED | APPROVED | DECLINED | WAITLISTED
  interview_at    TEXT,
  interview_link  TEXT,
  reviewer        TEXT,
  review_notes    TEXT,
  decided_at      TEXT,
  decision_reason TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_email ON applications(email);

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name          TEXT,
  role          TEXT NOT NULL DEFAULT 'CLIENT',    -- ADMIN|CLIENT
  customer_id   INTEGER REFERENCES customers(id) ON DELETE CASCADE,
  is_active     INTEGER NOT NULL DEFAULT 1,
  must_change_password INTEGER NOT NULL DEFAULT 0,
  last_login_at TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_customer ON users(customer_id);

CREATE TABLE IF NOT EXISTS quotes (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ref               TEXT UNIQUE NOT NULL,
  customer_id       INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  title             TEXT NOT NULL,
  description       TEXT,
  category          TEXT,
  quantity          INTEGER,
  quantity_unit     TEXT DEFAULT 'units',
  target_unit_price_cents INTEGER,
  materials         TEXT,
  dimensions        TEXT,
  color_finish      TEXT,
  packaging         TEXT,
  certifications    TEXT,
  destination_country TEXT,
  destination_city  TEXT,
  incoterm          TEXT DEFAULT 'DDP',
  needed_by         TEXT,
  status            TEXT NOT NULL DEFAULT 'NEW',
  -- NEW           just arrived, waiting to be accepted into the queue
  -- IN_REVIEW     accepted, being priced
  -- ESTIMATE_SENT priced and with the client
  -- ACCEPTED      the client accepted our estimate
  -- DECLINED      the client declined our estimate
  -- REJECTED      we declined to quote it
  -- EXPIRED       timed out
  priority          TEXT NOT NULL DEFAULT 'NORMAL',-- NORMAL|RUSH
  due_at            TEXT NOT NULL,                 -- 24h SLA deadline
  responded_at      TEXT,
  decided_at        TEXT,
  internal_notes    TEXT,
  decline_reason    TEXT,                          -- shown to the client if we reject it
  triaged_at        TEXT,
  triaged_by        TEXT,
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);

CREATE TABLE IF NOT EXISTS quote_files (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  quote_id    INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  filename    TEXT NOT NULL,
  stored_name TEXT NOT NULL,
  content_type TEXT,
  size_bytes  INTEGER,
  uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quote_files_quote ON quote_files(quote_id);

CREATE TABLE IF NOT EXISTS estimates (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  quote_id          INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  unit_price_cents  INTEGER NOT NULL,
  moq               INTEGER NOT NULL DEFAULT 1,
  quantity          INTEGER NOT NULL DEFAULT 1,
  tooling_cents     INTEGER NOT NULL DEFAULT 0,
  sample_cents      INTEGER NOT NULL DEFAULT 0,
  shipping_cents    INTEGER NOT NULL DEFAULT 0,
  duties_cents      INTEGER NOT NULL DEFAULT 0,
  lead_time_days    INTEGER NOT NULL DEFAULT 30,
  ship_method       TEXT,                          -- SEA|AIR|EXPRESS
  incoterm          TEXT,
  valid_until       TEXT,
  notes             TEXT,
  total_cents       INTEGER NOT NULL DEFAULT 0,
  created_by        TEXT,
  created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_estimates_quote ON estimates(quote_id);

CREATE TABLE IF NOT EXISTS crm_activities (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL DEFAULT 'NOTE',        -- NOTE|CALL|EMAIL|MEETING|SYSTEM
  body        TEXT NOT NULL,
  author      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_crm_customer ON crm_activities(customer_id);

CREATE TABLE IF NOT EXISTS calendar_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
  order_id    INTEGER,
  kind        TEXT NOT NULL DEFAULT 'MEETING',     -- CALL|MEETING|FACTORY|SHIPMENT|FOLLOWUP|DEADLINE
  starts_at   TEXT NOT NULL,
  ends_at     TEXT,
  all_day     INTEGER NOT NULL DEFAULT 0,
  location    TEXT,
  notes       TEXT,
  done        INTEGER NOT NULL DEFAULT 0,
  created_by  TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_start ON calendar_events(starts_at);

CREATE TABLE IF NOT EXISTS catalog_items (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  sku            TEXT UNIQUE NOT NULL,
  name           TEXT NOT NULL,
  category       TEXT,
  description    TEXT,
  specs          TEXT,
  materials      TEXT,
  unit_price_cents INTEGER NOT NULL DEFAULT 0,
  moq            INTEGER NOT NULL DEFAULT 1,
  lead_time_days INTEGER NOT NULL DEFAULT 30,
  image_url      TEXT,
  origin_quote_id INTEGER REFERENCES quotes(id) ON DELETE SET NULL,
  tags           TEXT,                             -- comma separated; any match grants access
  is_active      INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS catalog_assignments (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id           INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  customer_id       INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  custom_price_cents INTEGER,
  custom_moq        INTEGER,
  note              TEXT,
  assigned_by       TEXT,
  assigned_at       TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(item_id, customer_id)
);
CREATE INDEX IF NOT EXISTS idx_assign_customer ON catalog_assignments(customer_id);

CREATE TABLE IF NOT EXISTS orders (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ref               TEXT UNIQUE NOT NULL,
  customer_id       INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  source_quote_id   INTEGER REFERENCES quotes(id) ON DELETE SET NULL,
  status            TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
  -- PENDING_PAYMENT|PAYMENT_PROCESSING|IN_REVIEW|APPROVED|IN_PRODUCTION|SHIPPED|DELIVERED|CANCELLED|REFUNDED|ON_HOLD
  subtotal_cents    INTEGER NOT NULL DEFAULT 0,
  shipping_cents    INTEGER NOT NULL DEFAULT 0,
  tax_cents         INTEGER NOT NULL DEFAULT 0,
  fee_cents         INTEGER NOT NULL DEFAULT 0,   -- 1.5% convenience fee
  processing_fee_cents INTEGER NOT NULL DEFAULT 0, -- what the card/bank network charges, passed on
  freight_estimate_cents INTEGER NOT NULL DEFAULT 0,
  customs_estimate_cents INTEGER NOT NULL DEFAULT 0,
  freight_breakdown TEXT,                        -- JSON, so the estimate is auditable
  freight_waived    INTEGER NOT NULL DEFAULT 0,  -- owner absorbs freight + customs
  waived_by         TEXT,
  waived_at         TEXT,
  total_cents       INTEGER NOT NULL DEFAULT 0,
  currency          TEXT NOT NULL DEFAULT 'usd',
  payment_method    TEXT,                          -- CARD|ACH|WIRE
  payment_status    TEXT NOT NULL DEFAULT 'UNPAID',-- UNPAID|PROCESSING|PAID|FAILED|REFUNDED
  payment_provider  TEXT,
  payment_ref       TEXT,
  checkout_session_id TEXT,
  funds_confirmed_at TEXT,
  review_release_at TEXT,                          -- funds_confirmed_at + 24h
  reviewed_at       TEXT,
  reviewed_by       TEXT,
  review_notes      TEXT,
  production_started_at TEXT,
  shipped_at        TEXT,
  delivered_at      TEXT,
  carrier           TEXT,
  tracking_number   TEXT,
  ship_to           TEXT,
  notes             TEXT,
  orders_email_sent_at TEXT,
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE TABLE IF NOT EXISTS order_items (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id         INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  catalog_item_id  INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
  quote_id         INTEGER REFERENCES quotes(id) ON DELETE SET NULL,
  name             TEXT NOT NULL,
  sku              TEXT,
  unit_price_cents INTEGER NOT NULL DEFAULT 0,
  quantity         INTEGER NOT NULL DEFAULT 1,
  line_total_cents INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

CREATE TABLE IF NOT EXISTS order_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  event      TEXT NOT NULL,
  detail     TEXT,
  actor      TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_order_events_order ON order_events(order_id);

CREATE TABLE IF NOT EXISTS cart_items (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  item_id     INTEGER REFERENCES catalog_items(id) ON DELETE CASCADE,
  quote_id    INTEGER REFERENCES quotes(id) ON DELETE CASCADE,
  quantity    INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cart_customer ON cart_items(customer_id);

CREATE TABLE IF NOT EXISTS email_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  to_addr    TEXT NOT NULL,
  cc_addr    TEXT,
  subject    TEXT NOT NULL,
  body       TEXT,
  template   TEXT,
  status     TEXT NOT NULL DEFAULT 'SENT',
  error      TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS webhook_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  provider    TEXT NOT NULL,
  event_id    TEXT,
  event_type  TEXT,
  payload     TEXT,
  handled     INTEGER NOT NULL DEFAULT 0,
  note        TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_event ON webhook_log(provider, event_id);
