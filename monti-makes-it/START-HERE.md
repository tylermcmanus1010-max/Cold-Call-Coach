# Montano Makes That — complete build

Two things in this archive, and they are not the same thing.

```
engine/       the real application. A Flask + SQLite app you deploy and run the
              business on. This is the one that matters.

prototype/    a single self-contained HTML file. Double-click it and the whole
              site runs in your browser with demo data — no install, no server.
              For showing people. It is not the product.
```

---

## Run the engine

```bash
cd engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit it
export SECRET_KEY=dev

flask --app app seed          # database + demo data
flask --app app run           # http://localhost:5000
```

| Sign in as | Password | What you get |
|---|---|---|
| `Tyler1` | `Tyler1` | The admin portal |
| `client1` | `client` | A member with a product, a raised quote limit, freight waived |
| `client2` … `client5` | `client` | Quote-only members — nothing to buy yet |

Then read `engine/README.md`. It covers the money model, the fees, the freight
estimator, membership, tags, Stripe, email, and how to deploy.

## Open the prototype

Open `prototype/montano-prototype.html` in any browser. Same logins. Everything is
in-memory, so a refresh resets it and nothing is saved.

---

## What the engine does

**The public site** — one argument (we are the factory, so the price is the factory
price) and two doors: request a quote, or apply for membership.

**Quote intake** — four plain-language questions, a 24-hour clock, and an admin
triage queue where each request is accepted into pricing or declined with a reason
the client is actually sent.

**Membership** — applications are read by a person, an interview is booked (which
emails the applicant and lands on your calendar), and only acceptance creates a
portal login and unlocks buying. Every member gets 10 new quote requests per rolling
30 days, raisable per account.

**Member portals** — sealed per customer and provably so. Their quotes, their
estimates, their products, their purchases with an Ordered → Paid → Reviewed →
In production → Shipped → Delivered timeline and a tracking code.

**Catalog by tag** — an item reaches a portal when it carries a tag that member also
carries, or by direct assignment at a price negotiated for that account.

**Checkout** — card or bank transfer, priced separately and both totals shown before
they choose. Goods + freight + tax, then a 1.5% convenience fee, then Stripe's cut
passed through at cost and grossed up so the intended amount actually lands.

**Freight and customs** — estimated the way a forwarder does it (chargeable weight,
lane rate, handling, duty, entry fees), stored with its full breakdown, and shown
line by line. The owner can absorb it per order or as a standing offer, and the
client sees the figure struck through with their name on it.

**The 24-hour review gate** — every paid order sits in a manufacturer review before
anything is produced. `ship_order()` raises if it hasn't cleared; nothing routes
around it.

**Admin portal** — revenue across 1D / 7D / 21D / 45D / 90D / 180D / 365D with a
like-for-like comparison, incoming quotes, applications, CRM, calendar, items
catalog, order log, email log, settings, and one click into any client's portal as
they see it.

## Checks

```bash
cd engine
SECRET_KEY=test python3 tests/smoke.py    # 210 checks, end to end
python3 tests/audit.py                    # 30/30 features present in the engine
```

`tests/audit.py` walks the app's live route table rather than trusting notes, and
runs inside the smoke suite — so the engine cannot quietly fall behind.

---

## Before this goes live

1. **The demo names are placeholders.** Serena Williams, Keanu Reeves, Zendaya,
   Idris Elba and Rihanna are seed data for testing. A real person's name on a
   customer record reads as a real customer. Swap them in `engine/mmt/seed.py`.
2. **The freight rates are conservative estimates.** They're shown to clients struck
   through as the cost you're absorbing, which is only lawful because the number is
   genuine. Put your real lane rates in `engine/mmt/freight.py` — do not inflate them.
3. **The +54% / +31% on the landing page are illustrative.** Replace them with a real
   spread from a job you've quoted.
4. **Card surcharging has rules.** Passing Stripe's fee to the customer is banned in
   Connecticut, Massachusetts and Puerto Rico, capped at 3%, and may not be applied
   to debit cards — and Stripe doesn't tell you the card type before payment.
   `PASS_THROUGH_PROCESSING=false` turns it off.
5. **Change the seeded passwords**, set a real `SECRET_KEY`, and turn on
   `SESSION_COOKIE_SECURE`.

## Still open

- The Valentino International CRM was never ported — that session wasn't reachable,
  so the CRM and calendar here were built fresh to spec.
- Uploads go to local disk. Move to S3 or R2 before running on ephemeral hosting.
- No rate limit or honeypot on the public quote form.
- Admin accounts are password-only; two-factor belongs there before the team grows.
- The prototype is missing a few admin screens the engine has (applications queue,
  calendar, email log, settings, the review-gate buttons).
