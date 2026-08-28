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

-- ---------------------------------------------------------------------------
-- The public catalogue, registrations, and the numbers behind them (§8, §11)
--
-- Two record shapes that must never touch. A catalogue item carries what
-- everyone may see: a range, a typical MOQ, a lead time, and the plain-language
-- reason the range is a range. A registration carries what exactly one customer
-- may see: the price we agreed with them. §8.6 is explicit that the public
-- range is entered deliberately by an admin and is never derived from anybody's
-- negotiated price — so they live in different tables and are serialized by
-- different code, and a customer's price sitting outside the public range is
-- expected rather than an error.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS catalogue_registrations (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id        INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  customer_id    INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  unit_price_cents INTEGER,                      -- their negotiated price, if a flat one
  matrix_id      INTEGER REFERENCES price_matrices(id) ON DELETE SET NULL,
  moq            INTEGER,
  lead_time_days INTEGER,
  active         INTEGER NOT NULL DEFAULT 1,     -- deactivating gates them out immediately
  assigned_by    TEXT NOT NULL,
  assigned_at    TEXT NOT NULL DEFAULT (datetime('now')),
  deactivated_by TEXT,
  deactivated_at TEXT,
  notes          TEXT,
  UNIQUE(item_id, customer_id)
);
CREATE INDEX IF NOT EXISTS idx_reg_customer ON catalogue_registrations(customer_id, active);
CREATE INDEX IF NOT EXISTS idx_reg_item ON catalogue_registrations(item_id, active);

-- Every number a client sees resolves to a row here (§11.1). A rendered field
-- with no input id behind it is a P1, which is only enforceable if the input is
-- a real record with an author and a publish time rather than a literal in a
-- template.
CREATE TABLE IF NOT EXISTS pricing_inputs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id  INTEGER REFERENCES customers(id) ON DELETE CASCADE,
  item_id      INTEGER REFERENCES catalog_items(id) ON DELETE CASCADE,
  field        TEXT NOT NULL,                    -- what this number is
  value_cents  INTEGER,
  value_text   TEXT,
  entered_by   TEXT NOT NULL,
  entered_at   TEXT NOT NULL DEFAULT (datetime('now')),
  published_at TEXT,                             -- null until an admin publishes it
  published_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_inputs_item ON pricing_inputs(item_id, customer_id);

-- A price matrix is two axes, not a line (Appendix B): quantity tiers across,
-- spec/complexity tiers down. Boars Head's containers are priced off both.
CREATE TABLE IF NOT EXISTS price_matrices (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id  INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  item_id      INTEGER REFERENCES catalog_items(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  spec_axis_label TEXT NOT NULL DEFAULT 'Spec complexity',
  notes        TEXT,
  created_by   TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  published_at TEXT,                             -- nothing reaches a member before this
  published_by TEXT
);

CREATE TABLE IF NOT EXISTS price_matrix_cells (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  matrix_id     INTEGER NOT NULL REFERENCES price_matrices(id) ON DELETE CASCADE,
  quantity_min  INTEGER NOT NULL,
  quantity_max  INTEGER,                         -- null = open-ended top tier
  spec_tier     TEXT NOT NULL,
  unit_price_cents INTEGER NOT NULL,
  input_id      INTEGER REFERENCES pricing_inputs(id) ON DELETE SET NULL,
  UNIQUE(matrix_id, quantity_min, spec_tier)
);
CREATE INDEX IF NOT EXISTS idx_cells_matrix ON price_matrix_cells(matrix_id);

-- ---------------------------------------------------------------------------
-- Tooling (§11.3)
--
-- The client sees four facts and never a fifth, so the columns split by
-- audience: `client_*` is renderable, everything else is internal and is the
-- reason A31 can assert that no internal field reached a client payload.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tools (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ref            TEXT UNIQUE NOT NULL,
  item_id        INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
  customer_id    INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  client_description TEXT NOT NULL,              -- fact 1: what it is, in plain words
  client_cost_cents  INTEGER NOT NULL,           -- fact 2: one number, never a range
  status         TEXT NOT NULL DEFAULT 'QUOTED', -- QUOTED|PAID|IN_USE|RELEASED|RETIRED
  paid_at        TEXT,
  location       TEXT,
  condition      TEXT,
  last_used_at   TEXT,
  released_at    TEXT,
  from_previous_supplier INTEGER NOT NULL DEFAULT 0,
  arrival_condition TEXT,                        -- only for a tool that came from elsewhere
  internal_cost_cents INTEGER,                   -- never rendered to a client
  internal_notes TEXT,                           -- never rendered to a client
  created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tools_item ON tools(item_id);

-- ---------------------------------------------------------------------------
-- Item images (Tier IMG) and the manufacturing memory (§10.3, Product Genome)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item_images (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id      INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  stored_name  TEXT,                             -- a file under UPLOAD_DIR
  svg          TEXT,                             -- or an inline drawing, for a diagram
  caption      TEXT NOT NULL,                    -- every image has one (WI-P-06)
  source_label TEXT NOT NULL,                    -- and a source
  alt_text     TEXT NOT NULL,
  position     INTEGER NOT NULL DEFAULT 0,
  is_public    INTEGER NOT NULL DEFAULT 0,       -- public catalogue images only
  annotations  TEXT,                             -- JSON callouts for the diagram layer
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_images_item ON item_images(item_id, position);

CREATE TABLE IF NOT EXISTS item_genome (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id    INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  section    TEXT NOT NULL,                      -- one of the six client-facing sections
  body       TEXT,
  is_unknown INTEGER NOT NULL DEFAULT 0,         -- marked unknown, never a plausible default
  is_internal INTEGER NOT NULL DEFAULT 0,        -- the admin-only partition (GEN-07)
  updated_by TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(item_id, section, is_internal)
);

-- ---------------------------------------------------------------------------
-- Client agents (Appendix B, "Client agent contract")
--
-- One agent, one customer, and the binding is a foreign key rather than a
-- sentence in a prompt — which is what makes A30 provable. An agent proposes;
-- everything it produces lands in agent_proposals and enters through the same
-- admin publish step as any other input.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS client_agents (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ref            TEXT UNIQUE NOT NULL,
  customer_id    INTEGER NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
  status         TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE|SUSPENDED|REVOKED
  template_version TEXT NOT NULL,
  provisioned_at TEXT NOT NULL DEFAULT (datetime('now')),
  status_changed_at TEXT,
  status_reason  TEXT,
  scope_verified_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_proposals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id    INTEGER NOT NULL REFERENCES client_agents(id) ON DELETE CASCADE,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL,                     -- QUOTE_DRAFT|PRICE_NOTE|REORDER_NUDGE
  body        TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'PROPOSED',  -- PROPOSED|ACCEPTED|REJECTED
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  reviewed_by TEXT,
  reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_access_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id    INTEGER REFERENCES client_agents(id) ON DELETE SET NULL,
  agent_ref   TEXT NOT NULL,
  bound_customer_id INTEGER NOT NULL,
  requested   TEXT NOT NULL,                     -- what it asked for
  refused     INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Every admin look at a member's account, mirrored to the member (§10.4, ADM-11).
CREATE TABLE IF NOT EXISTS security_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  actor       TEXT NOT NULL,
  action      TEXT NOT NULL,
  reason      TEXT,
  mode        TEXT,                              -- READ_ONLY|WRITE
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_security_customer ON security_log(customer_id, created_at);

-- ---------------------------------------------------------------------------
-- The transaction ledger (§11.4)
--
-- The financial record of the business, and the shape of this table is the
-- doctrine made structural:
--
--   Derived, never typed.   A row is written by a money event. There is no
--                           admin route that creates or edits one, and a
--                           correction is a new row pointing at the old one
--                           through `reverses_id` — never an UPDATE.
--   It must reconcile.      Every row carries the order it belongs to, so
--                           ledger and order log can be compared line for line
--                           rather than in aggregate.
--   Revenue means settled.  `status` is the whole point. An ACH debit in flight
--                           is PENDING and excluded from every revenue total;
--                           it transitions to SETTLED in place rather than
--                           spawning a second row, which is why settlement is
--                           an UPDATE of `status` and not an INSERT.
--
-- `occurred_at` is stored UTC and `period_tz` names the timezone the period
-- views bucket by, once, for the whole ledger. §11.5.1 requires one stored
-- timezone: without it "which month is this in" has as many answers as there
-- are readers, and the month and quarter views drift apart at every boundary.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ledger_entries (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  receipt_no    TEXT UNIQUE NOT NULL,
  customer_id   INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id      INTEGER REFERENCES orders(id) ON DELETE SET NULL,
  order_ref     TEXT,                            -- kept so a deleted order still reconciles
  kind          TEXT NOT NULL,
  -- CHARGE | SETTLEMENT | REFUND | PARTIAL_REFUND | REVERSAL | MANUAL_CONFIRMATION | FEE
  status        TEXT NOT NULL,                   -- PENDING | SETTLED | FAILED
  method        TEXT,                            -- CARD | ACH | WIRE | PO
  gross_cents   INTEGER NOT NULL DEFAULT 0,      -- what the customer was charged
  fee_cents     INTEGER NOT NULL DEFAULT 0,      -- provider fee, admin-only
  net_cents     INTEGER NOT NULL DEFAULT 0,      -- gross - fee
  currency      TEXT NOT NULL DEFAULT 'usd',
  occurred_at   TEXT NOT NULL,                   -- UTC, the money event's own time
  period_tz     TEXT NOT NULL DEFAULT 'UTC',
  reverses_id   INTEGER REFERENCES ledger_entries(id) ON DELETE RESTRICT,
  confirmed_by  TEXT,                            -- the admin, on a manual confirmation
  review_outcome TEXT,                           -- the linked review, when there is one
  note          TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ledger_customer ON ledger_entries(customer_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ledger_order ON ledger_entries(order_id);
CREATE INDEX IF NOT EXISTS idx_ledger_when ON ledger_entries(occurred_at);

-- Reconciliation runs. A break is recorded and stays recorded; §11.4 forbids
-- closing one by adjusting the ledger, so the resolution field describes what
-- was done to the *other* side, never to a ledger row.
CREATE TABLE IF NOT EXISTS reconciliation_runs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ran_at        TEXT NOT NULL DEFAULT (datetime('now')),
  ledger_cents  INTEGER NOT NULL,
  order_log_cents INTEGER NOT NULL,
  provider_cents INTEGER,
  break_count   INTEGER NOT NULL DEFAULT 0,
  breaks        TEXT,                            -- JSON, one named break per entry
  resolved_at   TEXT,
  resolution    TEXT
);

-- ---------------------------------------------------------------------------
-- The Decision Room (Appendix E.1, §3.2 DR-*)
--
-- The unit is an *item*, not a quote. A quote request becomes one, auto-numbered
-- and unnamed; the client renames it whenever they like and the internal ref
-- never changes, so their name and our reference can both be true at once.
--
-- An item has no prices until an admin enters the cost inputs and publishes.
-- `published_at` is the gate: every read path filters on it, so "nothing
-- reaches a member before publish" is a WHERE clause rather than a habit.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decision_items (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ref           TEXT UNIQUE NOT NULL,            -- MMI-D-nnn, never changes
  auto_name     TEXT NOT NULL,                   -- "Unapproved item 003"
  client_name   TEXT,                            -- theirs, renameable, may be null
  customer_id   INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  quote_id      INTEGER REFERENCES quotes(id) ON DELETE SET NULL,
  catalog_item_id INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
  status        TEXT NOT NULL DEFAULT 'PENDING', -- PENDING | APPROVED
  stage         INTEGER NOT NULL DEFAULT 1,      -- 1 received, 2 in review, 3 priced
  source        TEXT,                            -- what they actually sent us
  outstanding   TEXT,                            -- what we still need, in their words
  received_at   TEXT NOT NULL DEFAULT (datetime('now')),
  published_at  TEXT,                            -- the gate; null = no prices exist
  published_by  TEXT,
  qty_min       INTEGER,                         -- slider bounds, entered not hard-coded
  qty_max       INTEGER,
  qty_step      INTEGER NOT NULL DEFAULT 100,
  target_unit_cents INTEGER,                     -- the client's target, theirs to set
  target_date   TEXT,
  is_fixture    INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ditems_customer ON decision_items(customer_id, status);

-- The three strategies, entered by the desk and published together. Each row is
-- what differentiates one route from another; the arithmetic that turns them
-- into a price lives in monti/decisionroom.py and reads only from here and from
-- the cost inputs.
CREATE TABLE IF NOT EXISTS item_strategies (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id       INTEGER NOT NULL REFERENCES decision_items(id) ON DELETE CASCADE,
  slot          INTEGER NOT NULL,                -- 0 lowest cost, 1 fastest, 2 certainty
  label         TEXT NOT NULL,
  title         TEXT NOT NULL,
  extra_cents   INTEGER NOT NULL DEFAULT 0,      -- what this route adds per unit
  lead_days     INTEGER NOT NULL,
  mode          TEXT NOT NULL DEFAULT 'ocean',   -- ocean | split | air
  production    TEXT,
  inspection    TEXT,
  footnote      TEXT,
  includes_lab  INTEGER NOT NULL DEFAULT 0,
  tooling_treatment TEXT NOT NULL DEFAULT 'amortized',
  UNIQUE(item_id, slot)
);

-- The levers offered under "what would need to change". Each is priced
-- independently against the entered curve — §11.1 forbids extrapolation, so a
-- lever whose saving was not entered simply is not offered.
CREATE TABLE IF NOT EXISTS item_levers (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id       INTEGER NOT NULL REFERENCES decision_items(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,                   -- spec | qty | pkg
  label         TEXT NOT NULL,
  note          TEXT,
  saving_cents  INTEGER NOT NULL DEFAULT 0,      -- qty levers price themselves
  active        INTEGER NOT NULL DEFAULT 1,
  UNIQUE(item_id, kind)
);

-- Freight lanes as admin inputs rather than constants. Every freight figure a
-- client sees resolves here (§11.1), and a lane nobody entered cannot be shown.
CREATE TABLE IF NOT EXISTS freight_lanes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  mode          TEXT UNIQUE NOT NULL,            -- ocean | split | air
  per_unit_cents INTEGER NOT NULL,
  fixed_cents   INTEGER NOT NULL,                -- spread across the run
  transit_label TEXT NOT NULL,
  lane_label    TEXT NOT NULL,
  entered_by    TEXT NOT NULL,
  entered_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- The Product Genome (Appendix E.3)
--
-- E.7 resolves the naming conflict in the prototype's favour, so the six
-- sections are: specification, golden sample, quality record, tooling,
-- landed-cost profile, history. `item_genome` already holds the six section
-- bodies; these tables hold the structured parts that are not prose.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item_revisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  rev         TEXT NOT NULL,
  changed_at  TEXT NOT NULL,
  change      TEXT NOT NULL,
  reason      TEXT NOT NULL,
  signed_by   TEXT,
  UNIQUE(item_id, rev)
);

CREATE TABLE IF NOT EXISTS golden_samples (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL UNIQUE REFERENCES catalog_items(id) ON DELETE CASCADE,
  ref         TEXT NOT NULL,
  sealed_at   TEXT,
  stored_at   TEXT,
  duplicate_held_by TEXT,
  reverify_at TEXT
);

CREATE TABLE IF NOT EXISTS quality_checks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  check_name  TEXT NOT NULL,
  method      TEXT NOT NULL,
  frequency   TEXT NOT NULL,
  accept      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_claims (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  run_ref     TEXT,
  raised_at   TEXT NOT NULL,
  summary     TEXT NOT NULL,
  resolution  TEXT,
  closed_at   TEXT
);

CREATE TABLE IF NOT EXISTS item_runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
  run_no      INTEGER NOT NULL,
  po_ref      TEXT,
  quantity    INTEGER NOT NULL,
  shipped_at  TEXT,
  promised_at TEXT,
  on_time     INTEGER,
  landed_unit_cents INTEGER,
  UNIQUE(item_id, run_no)
);

-- ---------------------------------------------------------------------------
-- Membership: capacity, the Factory Plan, and performance credits (E.4)
-- ---------------------------------------------------------------------------
-- §0.3 / MEM-06: ten quotes was the wrong unit. Capacity is weighted by the
-- engineering a request actually consumes, and the fairness rules run in the
-- member's favour — a declined or incomplete request costs nothing, and a
-- missed deadline returns the units automatically.
CREATE TABLE IF NOT EXISTS capacity_ledger (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  quote_id    INTEGER REFERENCES quotes(id) ON DELETE SET NULL,
  item_id     INTEGER REFERENCES decision_items(id) ON DELETE SET NULL,
  label       TEXT NOT NULL,
  classified  TEXT NOT NULL,                     -- the weight class, in words
  weight      INTEGER NOT NULL,                  -- 1 | 2 | 4
  outcome     TEXT NOT NULL,
  charged     INTEGER NOT NULL DEFAULT 0,        -- what was actually debited
  reason      TEXT,                              -- why it was not charged, if not
  occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_capacity_customer ON capacity_ledger(customer_id, occurred_at);

CREATE TABLE IF NOT EXISTS factory_plans (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
  written_at  TEXT NOT NULL,
  revised_at  TEXT,
  interview_by TEXT,
  first_product TEXT,
  annual_demand TEXT,
  method      TEXT,
  open_questions TEXT,
  testing     TEXT,
  first_order_path TEXT
);

-- Both commitment columns. §E4.02: a commitment with no measurable source says
-- so, rather than showing a figure nobody measured.
CREATE TABLE IF NOT EXISTS commitments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  side        TEXT NOT NULL,                     -- MEMBER | MONTI
  commitment  TEXT NOT NULL,
  measure     TEXT,                              -- null = not measurable yet
  met         INTEGER,                           -- null = unmeasured
  position    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS performance_credits (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  ledger_id   INTEGER REFERENCES ledger_entries(id) ON DELETE SET NULL,
  amount_cents INTEGER NOT NULL,
  reason      TEXT NOT NULL,
  detail      TEXT,
  issued_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Make This Box — a physical sample, tracked from the moment it leaves their
-- hands. Every stage advances on a recorded event (WI-I-07), never on a guess.
CREATE TABLE IF NOT EXISTS sample_boxes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ref         TEXT UNIQUE NOT NULL,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  item_id     INTEGER REFERENCES decision_items(id) ON DELETE SET NULL,
  requested_at TEXT NOT NULL DEFAULT (datetime('now')),
  stage       INTEGER NOT NULL DEFAULT 0,        -- 0 requested … 6 returned/stored
  seal_code   TEXT,
  disposition TEXT
);

CREATE TABLE IF NOT EXISTS sample_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  box_id      INTEGER NOT NULL REFERENCES sample_boxes(id) ON DELETE CASCADE,
  stage       INTEGER NOT NULL,
  happened_at TEXT NOT NULL DEFAULT (datetime('now')),
  detail      TEXT,
  recorded_by TEXT NOT NULL
);
