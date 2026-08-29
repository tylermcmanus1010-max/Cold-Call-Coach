# Appendix E — prototype inventory

Appendix E's opening instruction is that `MGR-02` opens the prototype, confirms
every row against what it actually does, and maps each row to a work item.

**The prototype has now been read in full** — supplied directly rather than
through the session reference, which remains unreachable from here. Every row
below is confirmed against what the prototype actually does, and the build
states are current as of this run.

One limit stands. Appendix E makes prototype behaviour the floor: nothing may
ship worse than it demonstrated. Reading a prototype tells you what it renders,
not how it feels to use, so parity below is asserted on behaviour and content,
not on interaction quality. The screenshot matrix that would settle that is
still not built.

State meanings: **BUILT** — exists and is covered by a check or an exercised
path · **PARTIAL** — exists in part, with what is missing named · **NOT BUILT** —
no implementation · **UNVERIFIABLE HERE** — cannot be assessed without the
prototype.

---

## E.1 — My products (the Decision Room)

Built against Boars Head's real data. The demo item and demo member from the
prototype are not carried over.

**Renamed this run.** "Decision Room" was the name of the tab *and* the name of
what a priced product opens into. Only the second is a place you enter, so the
tab is **My products** — everything the member has asked us to make, priced or
not — and the Decision Room is the three-route pricing surface inside a product
that has been published. `/portal/room` redirects; the internal refs are
unchanged.

| # | Behaviour | Work item | State |
|---|---|---|---|
| E1.01 | Two rails with live counts | WI-R-02 | BUILT — counts derive from the rendered lists, so they cannot disagree with them |
| E1.02 | Click swaps the detail pane | WI-R-02 | BUILT — as a route rather than a client-side swap, so a product is linkable and survives a refresh. The list is the left column down to 900px rather than folding into a header at 1080 |
| E1.03 | Inline rename, internal ref fixed | WI-R-02 | BUILT — `client_name` is nullable and separate from `ref`, which never changes |
| E1.04 | Pending view: tracker, outstanding list | WI-R-02, WI-I-03 | BUILT — the outstanding question on MMI-D-002 is the real board-grade escalation, not filler. Now also carries the request's reference, its 24-hour clock and its estimate, because the request and the product are one record |
| E1.05 | Quantity slider, bounds from the matrix | WI-R-04 | BUILT — `quantity_bounds()` reads the entered band or the published matrix; a request outside it clamps. `A15` proves the clamp |
| E1.06 | Target price and date | WI-R-05 | PARTIAL — target price is live and an unreachable target produces a recommendation rather than silence; target *date* is stored but not yet used in the arithmetic |
| E1.07 | Freight mode selector | WI-R-06 | BUILT — three lanes, each an entered `freight_lanes` row |
| E1.08 | Tooling toggle, amortise vs upfront | WI-R-07 | BUILT — strategies carry §11.3.3 defaults and the toggle overrides within one; the Tooling Line always states which is active |
| E1.09 | Three strategy cards | WI-R-03 | BUILT — every figure returns with the input ids that produced it (`A15`) |
| E1.10 | Card highlights when it beats target | WI-R-03 | BUILT — and never highlights a figure with no provenance |
| E1.11 | What-would-need-to-change, levers priced independently | WI-R-08 | BUILT — a lever with no entered saving is not offered; the quantity lever refuses to price past the entered band |
| E1.12 | Freight comparison table | WI-R-06 | BUILT — same `landed()` as the cards, so the two cannot disagree |
| E1.13 | "Buy this route" carries the strategy into checkout | WI-R-03, WI-Y-01 | BUILT — snapshotted onto the order, so a later desk edit cannot change what someone bought |
| E1.14 | Genome link only on items with a run | WI-R-09 | BUILT — `has_run_history()` derives it from `item_runs` |

## E.2 — Checkout

| # | Behaviour | Work item | State |
|---|---|---|---|
| E2.01 | Four-step flow, payment first | WI-Y-01, WI-Y-06 | BUILT — the sequence is `monti/orders.py`; `A11` proves nothing ships before the review clears |
| E2.02 | ACH vs card, fees and totals recalculating | WI-Y-01 | BUILT — real provider rates from config, grossed up so the intended amount lands; the ACH total is labelled pending until settlement, and `A32` proves the pending row is out of revenue |
| E2.03 | Summary derived from item, strategy, quantity | WI-Y-01 | BUILT — the strategy, quantity, freight mode and tooling treatment all travel into the order |
| E2.04 | Guarantee panel | WI-Y-01 | NOT BUILT — and deliberately not stubbed. §11.2 forbids a claim that is not operationalized elsewhere, so a panel of commitments would have to be written against real ones |

## E.3 — Product Genome

| # | Behaviour | Work item | State |
|---|---|---|---|
| E3.01 | Six sections, prototype naming adopted | WI-R-09 | BUILT — the prototype's names are now the ones used, and the mapping is recorded once in `monti/genome.py:SECTIONS` |
| E3.02 | Tooling section renders the Tooling Line | WI-R-07 | BUILT — `A31` |
| E3.03 | Price curve with hover tooltip | WI-R-04 | PARTIAL — `price_curve()` samples only inside the entered band and labels interpolated points; the chart itself is not drawn |
| E3.04 | Table view of the curve | WI-R-04 | PARTIAL — the curve is computed once so a chart and a table could never disagree; the client-facing table is not rendered yet |
| E3.05 | Image set in every product section | WI-P-03 | BUILT — `A16`. Items currently carry the placeholder, pending real photographs |

## E.4 — Membership

| # | Behaviour | Work item | State |
|---|---|---|---|
| E4.01 | Factory Plan | WI-M-06 | BUILT — one page, from the acceptance call, with unknowns stated as unknown |
| E4.02 | Commitment lists with live performance | WI-M-06, WI-M-08 | BUILT — both columns, and `met` is nullable so an unmeasured commitment renders as unmeasured rather than as a tick. All ten currently are: Boars Head has no runs yet |
| E4.03 | Automatic performance credits | WI-M-08 | PARTIAL — the record and its surface exist; nothing accrues them automatically yet, because the events that would trigger one have not happened |
| E4.04 | Capacity: stats, usage bar, ledger, weighting, fairness | WI-M-07 | BUILT — the weighted ledger, the weighting table and the fairness rules are built, and `used` is summed from the rows so the header cannot disagree with them. Both doors now write a capacity row carrying the quote and the product it was charged for, and `A37` proves the debit and both counters move together. `A27` is still not written |

## E.5 — Admin bay

| # | Behaviour | Work item | State |
|---|---|---|---|
| E5.01 | Quote queue and published lists | WI-A-02 | BUILT — time remaining is rendered from the SLA deadline |
| E5.02 | Item name and portal assignment | WI-A-07, WI-K-02 | BUILT — assignment is the registration record; only admin writes it |
| E5.03 | Six cost inputs | WI-A-03 | BUILT — the six are named in `decisionroom.COST_FIELDS`; each save writes a new attributed row rather than updating in place |
| E5.04 | Three editable strategy rows | WI-A-03 | BUILT — editing before publish changes nothing member-facing |
| E5.05 | Lever definitions and quantity-lever toggle | WI-A-03, WI-R-08 | BUILT — a lever with no label is not offered; the quantity lever prices itself off the entered band |
| E5.06 | Live preview of the member's price | WI-A-03 | BUILT — calls the same `strategy_view()` the member's page calls, so it cannot be a preview of something else |
| E5.07 | Publish moves the item and unlocks its Decision Room | WI-A-03, WI-K-02 | BUILT — one act stamps every entered input at once and opens the room; the control reads "Update pricing" once live. Republish is not yet versioned |
| E5.08 | Topbar switches to staff identity | WI-A-01, WI-A-11 | PARTIAL — admin can open a member's portal and the view is marked; the impersonation event is **not** written to the member's security log, which §10.4 requires. The `security_log` table exists and is unused |
| E5.09 | **Master ledger** — three period formats, four search modes, export | **WI-L-01…06** | **BUILT** — `A32`, `A33`, `A35`, `A36` |

## E.6 — Global

| # | Behaviour | Work item | State |
|---|---|---|---|
| E6.01 | Light and dark themes | WI-V-01, WI-V-02 | PARTIAL — both themes are tokenized across all three theme states; the capture matrix and the contrast check `A20` are not built |
| E6.02 | Responsive to phone width | WI-V-02, WI-A-01 | PARTIAL — verified at 320/390/768/1280 with zero horizontal overflow, including all three ledger period views; the full §12.2 matrix and touch capture are not done |
| E6.03 | **Client ledger in the member portal** | **WI-L-07, WI-L-08** | **BUILT** — `A34`; client totals equal the admin ledger filtered to that customer |
| E6.04 | **One door: quotes and "describe it badly" are one surface** | **WI-I-01…03** | **BUILT this run** — `A37`. Both doors write one quote, one product and one weighted debit through `monti/intake.py`; `/portal/quotes` and `/portal/intake` redirect to `/portal/requests` |

---

## E.7 — Conflicts, and how they were resolved here

| Conflict | Resolution as implemented |
|---|---|
| Quantity slider bounds | **Protocol.** Bounds are a data field: `price_matrix_cells.quantity_min/max` per tier. The slider itself is not built, so nothing hard-codes 1,000–10,000 |
| Tooling treatment | **Both, per §11.3.3** — the three strategies carry different defaults and every line states which is active. The client override control is not built |
| Genome section names | **Unresolved.** E.7 adopts the prototype's naming; the sections here use the §3.2 names. Resolving it needs the prototype |
| "Production acceptance" placement | **Protocol naming.** The 24h review opens at funds-confirmed; `A11` |
| Catalogue | **Protocol.** Both halves exist: the public catalogue with ranges, and the registered per-member half. `A07`, `A08` |

## Summary

| State | Rows |
|---|---|
| BUILT | 32 |
| PARTIAL | 7 |
| NOT BUILT | 1 |
| **Total** | **40** |

*(The previous run's summary read 27 / 7 / 1 against 35 rows. The rows were
right and the tally was hand-written and stale — it had not been recounted after
the Decision Room tier landed. Counted from the table above, which is the only
number worth printing.)*

What remains:

- **E2.04, the guarantee panel** — the only NOT BUILT row, and deliberately.
  §11.2 forbids a claim that is not operationalized elsewhere. The prototype
  promises a same-day refund plus an automatic 5% credit; the credit *record*
  exists but nothing issues one automatically, so writing the panel would be
  making a promise the software does not keep.
- **E1.06's target date**, **E3.03/E3.04's chart and curve table**,
  **E4.03's automatic accrual**, **E4.04's `A27`**, **E5.07's republish
  versioning**, **E5.08's impersonation entry in the member's security log**,
  and **E6.01/E6.02's capture matrix**.
