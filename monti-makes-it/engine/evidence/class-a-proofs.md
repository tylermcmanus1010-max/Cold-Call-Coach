# Class A proofs

One block per check. A check counts toward Class A coverage only when the
defect its proof introduced was caught and named — §2.4, and §1.6's rule that
counting an unproven check toward coverage is itself a P0.

## A05 — Tenant isolation on every member-scoped route and asset URL

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** own_or_404 scoping clause removed -> /portal/quotes/1 — returned 200 — another member's row was served

## A06 — Brand and claim scanner (source, database, rendered, email)

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** source: 'we own the factory' in home.html -> monti/templates/public/home.html:26; database: old brand in settings.value -> db:settings.value#1; rendered: old brand injected into config, not source -> render:/:6

## A07 — Order gating refused server-side at all three points

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** add-to-cart -> portal.cart_add — add-to-cart for unregistered item 3 returned 302, expected a refusal; order-create -> portal.cart_checkout — an order was created containing unregistered item 3; checkout-start -> portal.checkout — checkout opened for order 12 on unregistered item 3

## A08 — No negotiated price, customer or assignment field in a public response

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** payload: negotiated price added to the public serializer -> public_item(MMI-B-0102) — fields outside the public set: ['unit_price_cents']; rendered: owning customer printed on the public page -> render:/catalogue/MMI-B-0102 — customer name 'Boars Head' in a public response

## A11 — An order cannot ship before its manufacturer review clears

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** ship_order's review guard removed -> orders.ship_order — shipped order 13 with no cleared review and did not raise

## A14 — Zero fixture rows, zero orphans, every customer has an agent

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** a seeded customer put back -> customers — 1 fixture row(s) survived the purge; an orphan line with no order -> order_items.order_id — 1 row(s) point at a orders row that is gone

## A15 — Every rendered Decision Room figure traces to a published input

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** provenance dropped from the arithmetic -> MMI-D-001 · strategy 0.ex_works_cents — does not carry the material input (17) it was computed from — part of the trail was dropped; an input unpublished under a live price -> MMI-D-001 · strategy 0 — rendered with no admin input behind it; the quantity band widened past the entered curve -> MMI-D-001 — quoted at 5,000,000 units, past the 500,000 an admin actually entered — that price was extrapolated

## A16 — Every item page carries a viewer or an explicit empty state

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** viewer removed from the public item page -> public:/catalogue/MMI-B-0101 — neither an image viewer nor an explicit empty state is present

## A30 — A client agent's queries cannot reach another customer

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** customer_id dropped from the agent's WHERE clause -> CLI-01.search_customers — reached customer 2 with prompt 'Probe Counterparty'

## A31 — Tooling disclosure: four facts, ownership, treatment, threshold

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** a fifth fact added to the line -> tool MMI-T-2001 / lowest_cost — a fifth fact was added: ['expected_lifespan']; the ownership sentence stripped -> tool MMI-T-2001 / lowest_cost — the ownership sentence is missing from the tooling line; the materiality threshold moved off 5% -> tool MMI-T-2001 — at 119,999 units the share is 0.0500 but no callout fired

## A32 — Ledger completeness and reconciliation

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** a money event's row deleted -> order MMI-O-L001 — paid, but wrote no ledger row; one payment recorded twice -> order MMI-O-L001 — 2 charge rows for one order — a money event wrote twice

## A33 — Period arithmetic: three views, one total, clean boundaries

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** the quarter boundary moved by one second -> ledger.periods(quarter) 2026-Q1 — holds 270000 but the months inside it sum to 430000 — the two views bucket by different clocks; a month bucket dropped from the view -> ledger.periods(month) — buckets sum to 590000 but the grand total is 840000

## A34 — Ledger tenancy, and client totals equal to the admin's for them

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** the client scope dropped from the ledger query -> ledger.search(client) — returned a row belonging to customer 2; our fee added to the client payload -> receipt MMI-R-100005 — client payload carries ['fee_cents']

## A35 — Export fidelity: the export is the screen

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** a column added to the export -> ledger.to_export — admin export columns are ['receipt_no', 'occurred_at', 'company_name', 'order_ref', 'kind', 'status', 'method', 'gross_cents', 'fee_cents', 'net_cents', 'internal_margin_cents'], expected ['receipt_no', 'occurred_at', 'company_name', 'order_ref', 'kind', 'status', 'method', 'gross_cents', 'fee_cents', 'net_cents']; a row dropped from the export -> ledger.to_export — exported 4 rows for 5 on screen

## A36 — Search completeness across all four modes

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** member search dropping a match -> ledger.search(member) — returned 8 rows for Boars Head, 9 exist; a search truncating silently -> ledger.search(date) — 4 + 5 != 5 — the range boundary drops or double-counts a row

## A37 — Every request writes one quote, one product and one debit, linked

- **Result on the current build:** pass
- **Proof:** caught
- **Defect introduced and reverted:** the door wrote a quote with no product -> POST /portal/requests — the door raised instead of answering — TypeError: 'NoneType' object is not subscriptable; the product was created without the link back to the request -> POST /portal/requests — wrote no product linked to the quote — the member has a reference with nothing behind it; the capacity debit lost the request it was charged for -> MMI-Q-1002 / MMI-D-004 — the capacity row does not carry the quote id, so the debit cannot be traced back to the request that caused it
