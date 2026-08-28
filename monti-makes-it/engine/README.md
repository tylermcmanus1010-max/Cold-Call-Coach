# Monti Makes It

Contract manufacturing platform. We are the factory, so there is no catalogue to browse —
you tell us what you want made and we quote it direct. Two doors on the public site and
nothing else competing for attention:

- **Request a Quote** — open to anyone. A landed price inside 24 hours.
- **Apply for Membership** — screened, interviewed over video, decided by a person.
  Membership is what unlocks buying.

```
Request a Quote  →  24h SLA  →  Admin prices it  →  Landed estimate emailed / in portal
Apply for Membership  →  read by a person  →  video interview  →  accepted or not

  member accepts estimate  →  Order  →  ACH / card checkout  →  FUNDS CONFIRMED
     →  Centralized orders email fires  →  24h manufacturer review gate
     →  Production  →  Shipped  →  reorder from their private catalogue
```

Every member may open **10 new quote requests per rolling 30 days**, raisable per account
for loyal customers.

---

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit it
export SECRET_KEY=dev

flask --app app seed          # creates the database + demo data
flask --app app run           # http://localhost:5000
```

Demo logins created by `seed`:

| Role                          | Sign in as                | Password    |
|-------------------------------|---------------------------|-------------|
| Admin                         | `Tyler1`                  | `Tyler1`    |
| Serena Williams (limit 16, has a product, freight waived) | `client1` | `client` |
| Keanu Reeves                  | `client2`                 | `client`    |
| Zendaya                       | `client3`                 | `client`    |
| Idris Elba                    | `client4`                 | `client`    |
| Rihanna                       | `client5`                 | `client`    |
| Member (demo book)            | dana@halcyongoods.com     | member2026  |
| Member (demo book)            | marcus@gritgrain.co       | member2026  |

> **The celebrity names are test placeholders.** Swap them in `monti/seed.py` before anyone
> outside the team sees this — a real person's name on a customer record reads as a real
> customer, which is a claim you don't want to be making by accident.

Accounts 2–5 are **quote-only**: accepted members with nothing assigned to their portals, so
all they can do is request a detailed quote. That's the state a new member starts in — their
catalogue fills up as you build things for them. Account 1 has a product, a raised quote
limit, and a standing freight waiver, so both states are visible side by side.

## Keeping the engine honest

`tests/audit.py` walks the app's live route table and module surface and asserts that every
feature this project has shipped is actually present — the two doors, the SLA, membership and
the interview flow, the quote cycle, revenue across all seven periods, incoming-quote triage,
the CRM, catalog tags, the calendar, open-any-portal, purchased items, both fee lines, the
freight estimator, the review gate, the orders email, Stripe with ACH, CSRF. It runs as part
of `tests/smoke.py`, so the engine cannot quietly fall behind the demo.

    python3 tests/audit.py        # 30/30 present

The seed also loads five membership applications in different states — one new, one with
an interview booked, two accepted, one declined — so the applications queue has something
in it.

**Change the admin password immediately in production**, or skip `seed` entirely and
create the first admin with `flask --app app init-db` followed by a one-liner:

```bash
python3 -c "
from monti import create_app; from monti.auth import create_user
app = create_app()
with app.app_context():
    create_user('you@montimakesit.com', 'a-strong-password', name='Tyler Monti', role='ADMIN')
"
```

Run the end-to-end test suite any time:

```bash
SECRET_KEY=test python3 tests/smoke.py
```

It walks every screen, verifies client isolation, and exercises the whole money path
including ACH settlement and the review gate.

---

## What's in here

```
app.py                    entry point (gunicorn app:app)
monti/
  __init__.py             app factory, template filters, error pages
  config.py               every setting, all from environment variables
  schema.sql              the database schema
  db.py                   thin SQLite layer (plain SQL — portable to Postgres)
  auth.py                 login, roles, CSRF, and the client-isolation gate
  membership.py           acceptance, the interview flow, and the quote cycle
  orders.py               order lifecycle: funds → review → production → shipped
  payments.py             Stripe Checkout over REST + a mock provider for dev
  mail.py                 SMTP or log-only delivery, everything audited
  seed.py                 demo data
  blueprints/
    public.py             the two doors: quote intake + membership application
    portal.py             client portal (sealed per customer)
    admin.py              admin portal: revenue, applications, CRM, calendar, catalog, orders
  analytics.py            revenue by period — 1d / 7d / 21d / 45d / 90d / 180d / 365d
    webhooks.py           Stripe webhook — the source of payment truth
  templates/              Jinja templates (public / portal / admin / email)
  static/css/app.css      the whole design system, one file
tests/smoke.py            end-to-end test
```

---

## Incoming quotes

Requests land at `NEW` and sit in `/admin/incoming` — oldest first, SLA clock running — until a
person decides. **Accept** moves it to `IN_REVIEW` for pricing (the clock is not reset) and emails
the client that it's with the floor. **Decline** marks it `REJECTED`, stores the reason, and emails
that reason to the client. A request can only be triaged once. Nothing can sit silently.

`DECLINED` still means *the client declined our estimate*; `REJECTED` means *we declined to quote it*.
Two different directions, two different words.

## Tags: how a catalog item reaches a portal

An item reaches a member one of two ways:

- **a tag** — the item carries tags, the member carries tags, any overlap grants access. One tag
  opens a whole range to a whole segment at once, and a member can hold as many tags as you like.
- **a direct assignment** — one item, one member, optionally at a price and MOQ negotiated for that
  account alone.

A direct assignment always wins on price. `monti/catalog.py` is the only place that logic lives:
`items_for_customer()` for the portal, `customers_for_item()` for the catalog page, `all_tags()` for
the tag index. Edit tags on an item from its catalog page, on a member from their CRM record — both
take effect immediately.

## Purchased items and tracking

`/portal/purchases` is every item a member has ever bought, grouped by order, each with a real
timeline — Ordered, Paid, Reviewed, In production, Shipped, Delivered — built from actual
timestamps, so a stage with no date genuinely hasn't happened. A tracking code appears with a copy
button as soon as one exists.

You set or change tracking from the admin order page at any point after payment, with an optional
"email them the code" tick. Every change is recorded on the order's audit trail.

## The money on an order

    goods                     line items
  + freight & customs         the estimate, or zero when the owner absorbs it
  + tax
  + convenience fee           1.5% of the above          PURCHASE_FEE_PERCENT
  + payment processing        what the network charges, at cost
  = total

Two fee lines, and nothing else anywhere in the system.

**The convenience fee** is 1.5%, computed in `orders.fee_on()` and applied only in
`recalc_totals()`, so it can't drift.

**Payment processing** is Stripe's cut, passed through at cost and *grossed up* so the amount we
intend to net actually lands: `T = (N + fixed) / (1 - rate)`, and the quoted fee is `T − N`. Charging
a flat 2.9% of the subtotal would leave us short; charging more than Stripe takes would breach both
their rules and US surcharging law. Card and ACH are priced separately and both totals are shown on
the checkout screen before the member chooses — ACH is usually a rounding error next to a card, so
showing both is the honest nudge. `PASS_THROUGH_PROCESSING=false` absorbs it instead.

Both fees appear as their own Stripe line items, so Stripe is asked for exactly our total.

## Freight, customs, and the owner's offer

`monti/freight.py` estimates what shipping an order actually costs: chargeable weight (actual vs
volumetric), a per-kg lane rate, origin and destination handling, duty at the published rate for that
kind of good, and US entry fees. Every component is stored on the order as JSON and rendered line by
line in the UI, for both the client and the admin.

The owner can **absorb** it — per order, or as a standing offer on a customer record. When absorbed,
the client sees the figure struck through, tagged
*"Owner tagged for customer #MMI-C-1001 — Freight & Customs Tax: Free"*, with the breakdown one click
away.

That redline is only defensible because the number is a real estimate. A struck-through figure the
customer was never going to pay is a fabricated reference price — illegal under FTC §5 and the EU
Omnibus Directive, and the first thing a sharp buyer tests. **Do not inflate this estimate to make
the gesture look larger.** The rates in `freight.py` are deliberately conservative for that reason;
if your real lane rates differ, change them there and the whole system follows.

`shipping_cents` always holds what the freight *costs*; `freight_waived` decides whether it's
*charged*. Taking the offer back restores the real figure rather than having lost it.

## Checkout

`/portal/orders/<id>/checkout` is our own screen: what they're buying, then card or bank transfer.
The chosen method is passed to Stripe, so the Checkout Session offers exactly that one and the page
they land on matches the button they pressed. ACH leaves the order in `PAYMENT_PROCESSING` until
settlement — the review window and the orders email fire on confirmed funds, never on initiation.

## The admin portal

`/admin/revenue` is the money view: a headline figure with a comparison against the prior
period of the same length, a chart, orders / average order / daily average, and revenue
broken down by client — all switchable across **1D, 7D, 21D, 45D, 90D, 180D, 365D**.

Revenue books on the day funds are **confirmed**, not the day the order is placed, so the
dashboard and the review gate can never disagree. `monti/analytics.py` is the only place that
maths lives.

From the CRM, the revenue table, or the sidebar you can **open any client's portal** exactly
as they see it (`/admin/clients/<id>/open`). The session is banner-marked the whole time and
one click steps back out. It is read-through only — writes still record the admin as the actor.

## Membership and the quote cycle

**Anyone can ask for a price. Only accepted members can buy.** A quote request from a
stranger creates a customer record at `membership_status = PROSPECT` and emails them the
estimate — no portal, no checkout. Applying is a separate form; the application is read in
the admin bay, an interview is booked (which emails the applicant and lands on your
calendar), and then it's accepted, waitlisted or declined with a reason the applicant is
shown. Acceptance is the only thing that creates portal credentials and unlocks payment.

In the code, `member_only` wraps the three routes that spend money — accepting an estimate,
creating an order from the cart, and starting checkout. Everything else stays open.

**The cycle.** `customers.quote_limit` (default 10) and `customers.quote_cycle_days`
(default 30) are per-account. `membership.quota_state()` counts quotes created inside the
rolling window; `check_quota()` returns the message shown when it's full, including when the
next slot opens. Raise a member's limit on their CRM page — the default for *new* members is
the `QUOTE_LIMIT` env var, but every existing account keeps whatever you set for it.

## The three rules the code enforces

**1. Clients cannot see each other.**
Every portal query is scoped to `g.user['customer_id']`, and anything fetched by id passes
through `own_or_404()` in `monti/auth.py`. Guessing another client's order id returns 404,
not their data. A catalog item that isn't assigned to you doesn't exist as far as your
portal is concerned. The test suite asserts all of this.

**2. Nothing ships without clearing the review.**
`orders.ship_order()` calls `review_state()` first and raises if the review isn't complete.
There is no path in the UI or the API that bypasses it. The countdown is visible to both
sides, and the deadline is auto-added to the admin calendar.

**3. The orders inbox is emailed on confirmed funds — not on initiated payment.**
`orders.confirm_funds()` is the only place that sends it, it's idempotent (a duplicate
webhook does nothing), and for ACH it fires on settlement, not on submission. An ACH debit
in flight leaves the order in `PAYMENT_PROCESSING` with no review window and no email.

---

## Payments

Set `PAYMENT_PROVIDER=stripe` and add your keys. The integration uses Stripe's REST API
directly (no SDK dependency) and creates a Checkout Session with both `card` and
`us_bank_account` enabled.

Point a Stripe webhook at:

```
https://your-domain.com/webhooks/stripe
```

and subscribe to:

- `checkout.session.completed` — card payments confirm here; ACH lands as *processing*
- `checkout.session.async_payment_succeeded` — ACH settled → funds confirmed
- `checkout.session.async_payment_failed`
- `charge.refunded`

Signatures are verified with the same HMAC-SHA256 scheme as the official library
(`payments.verify_webhook`). Every event is recorded in `webhook_log` with a unique index
on `(provider, event_id)`, so retries are harmless.

For wire transfers and POs, leave the order unpaid and use **Confirm funds received** on
the admin order page — it runs the identical downstream flow.

With `PAYMENT_PROVIDER=mock` (the default) you get an in-app simulated bank at checkout
that can settle a card instantly, hold an ACH debit as pending, or decline. Useful for
walking the whole flow before your Stripe account is live.

---

## Email

`MAIL_PROVIDER=log` records every message in the database without sending — good for
staging. `MAIL_PROVIDER=smtp` delivers through any SMTP host (Postmark, SES, Google
Workspace). Either way every message lands in the **Email log** in the admin bay, so you
can always prove what was sent.

Messages the system sends:

| Trigger | To | Template |
|---|---|---|
| Quote submitted | requester (member or not) | `quote_received` |
| Quote submitted | `QUOTES_EMAIL` | `quote_internal` |
| Membership applied for | applicant | `application_received` |
| Membership applied for | `APPLICATIONS_EMAIL` | `application_internal` |
| Interview booked | applicant | `application_interview` |
| Application accepted | new member (with credentials) | `application_approved` |
| Application declined or waitlisted | applicant | `application_declined` |
| Estimate sent | client | `estimate_ready` |
| **Funds confirmed** | **`ORDERS_EMAIL`** | `order_internal` |
| Funds confirmed | client | `order_receipt` |
| Review cleared | client | `order_approved` |
| Order held | client | `order_held` |
| Shipped | client + `ORDERS_EMAIL` | `order_shipped` |
| Portal created manually | client | `portal_invite` |

---

## Deploying

Any host that runs a Python web process works. The app is a single gunicorn process with
a SQLite file and an uploads directory — both need to live on a **persistent disk**.

**Render / Railway / Fly**

1. Push this repo to GitHub.
2. Create a web service from it. Build: `pip install -r requirements.txt`.
   Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`.
3. Attach a persistent volume mounted at `/data`.
4. Set env vars from `.env.example`, plus `DATABASE_PATH=/data/monti.db` and
   `UPLOAD_DIR=/data/uploads`.
5. Run `flask --app app init-db` once in a shell on the instance.
6. Set `SESSION_COOKIE_SECURE=true` and point `SITE_URL` at your domain.

**Docker**

```bash
docker build -t monti .
docker run -p 8000:8000 --env-file .env -v monti-data:/app/instance monti
```

**Moving to Postgres.** Every statement in `monti/db.py` and the blueprints is plain SQL.
Swap the `sqlite3` connection for `psycopg`, change `?` placeholders to `%s`, and change
`datetime('now')` defaults to `now()` in `schema.sql`. Nothing else in the app knows what
database it's talking to.

---

## Things worth doing next

- **A cron for the SLA.** Nothing currently auto-expires a stale quote or nudges you at
  hour 20. A daily job hitting a small admin endpoint would close that.
- **Interview scheduling is manual.** You pick a time and the applicant is emailed it. A
  Calendly-style pick-your-slot page would remove the back-and-forth.
- **Real file storage.** Uploads go to local disk. On a host with an ephemeral filesystem
  that's a data-loss risk — move to S3 or Cloudflare R2.
- **Rate limiting on `/quote`.** It's an open form. A honeypot field plus per-IP throttling
  before you advertise it widely.
- **Two-factor on admin accounts**, given the admin bay can see every customer.
