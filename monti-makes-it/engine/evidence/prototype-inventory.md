# Appendix E — prototype inventory

Appendix E's opening instruction is that `MGR-02` opens the prototype in session
`cse_01B2fEc4ZUQ49QMhmcd672yq`, confirms every row against what it actually
does, and maps each row to a work item.

**The first half of that could not be done here, and saying so is the point.**
That session is not reachable from this environment. I cannot open the
prototype, so I cannot confirm any row against its real behaviour, and I have
not pretended to: every row below is mapped from Appendix E's own description of
it. Where a row's build state depends on what the prototype actually did — E1.11's
lever combinations, E4.02's commitment lists, E5.06's byte-identical preview —
the state says so rather than guessing.

Appendix E also says prototype behaviour is the floor and nothing may ship worse
than the prototype demonstrated. **I cannot certify that against a prototype I
cannot see.** That is a genuine gap, not a formality: this inventory maps and
tracks, it does not verify parity.

State meanings: **BUILT** — exists and is covered by a check or an exercised
path · **PARTIAL** — exists in part, with what is missing named · **NOT BUILT** —
no implementation · **UNVERIFIABLE HERE** — cannot be assessed without the
prototype.

---

## E.1 — Decision Room

The Decision Room tier (`DR-*`) was not in the earlier run's scope and is not in
this one. Every row here is NOT BUILT, and that is the largest single gap
against Appendix E.

| # | Behaviour | Work item | State |
|---|---|---|---|
| E1.01 | Two rails with live counts | WI-R-02 | NOT BUILT |
| E1.02 | Click swaps the detail pane | WI-R-02 | NOT BUILT |
| E1.03 | Inline rename, internal ref fixed | WI-R-02 | NOT BUILT |
| E1.04 | Pending view: tracker, capacity charged, outstanding list | WI-R-02, WI-I-03 | NOT BUILT |
| E1.05 | Quantity slider, bounds from the matrix | WI-R-04 | NOT BUILT — see the conflict note below |
| E1.06 | Target price and date | WI-R-05 | NOT BUILT |
| E1.07 | Freight mode selector | WI-R-06 | PARTIAL — `monti/freight.py` estimates ocean and air per lane with a stored breakdown, but there is no Decision Room selector over it |
| E1.08 | Tooling toggle, amortize vs upfront | WI-R-07 | PARTIAL — `monti/tooling.py` implements all three strategy treatments and states which is active on every line; the client-facing override control does not exist |
| E1.09 | Three strategy cards | WI-R-03 | NOT BUILT |
| E1.10 | Card highlights when it beats target | WI-R-03 | NOT BUILT |
| E1.11 | What-would-need-to-change, levers priced independently | WI-R-08 | NOT BUILT |
| E1.12 | Freight comparison table | WI-R-06 | NOT BUILT |
| E1.13 | "Buy this route" carries the strategy into checkout | WI-R-03, WI-Y-01 | NOT BUILT |
| E1.14 | Genome link only on items with a run | WI-R-09 | PARTIAL — the genome exists and renders; the link's presence is not derived from run history |

**E1.05, and the conflict at E.7.** The protocol is emphatic that the slider
bounds come from the published price matrix per item and never from a hard-coded
1,000–10,000, because at $0.14–$0.20 a container that range is a $140–$2,000
order. The slider is not built, so the bug is not present — but the data it would
need *is*: `price_matrix_cells` carries `quantity_min` and `quantity_max` per
tier, so bounds are already a data field rather than a UI constant. Boars Head's
lowest tier starts at 20,000. Their real order range remains an open question
filed under §18.2, not guessed.

## E.2 — Checkout

| # | Behaviour | Work item | State |
|---|---|---|---|
| E2.01 | Four-step flow, payment first | WI-Y-01, WI-Y-06 | BUILT — the sequence is `monti/orders.py`; `A11` proves nothing ships before the review clears |
| E2.02 | ACH vs card, fees and totals recalculating | WI-Y-01 | BUILT — real provider rates from config, grossed up so the intended amount lands; the ACH total is labelled pending until settlement, and `A32` proves the pending row is out of revenue |
| E2.03 | Summary derived from item, strategy, quantity | WI-Y-01 | PARTIAL — derived from the item and quantity; there is no strategy to carry, because E1.09 is not built |
| E2.04 | Guarantee panel | WI-Y-01 | NOT BUILT — and deliberately not stubbed. §11.2 forbids a claim that is not operationalized elsewhere, so a panel of commitments would have to be written against real ones |

## E.3 — Product Genome

| # | Behaviour | Work item | State |
|---|---|---|---|
| E3.01 | Six sections, prototype naming adopted | WI-R-09 | PARTIAL — six sections exist with unknowns marked, but under the §3.2 names. E.7 says the prototype's naming wins; adopting it needs the prototype, so this is **UNVERIFIABLE HERE** and the mapping is unwritten |
| E3.02 | Tooling section renders the Tooling Line | WI-R-07 | BUILT — `A31` |
| E3.03 | Price curve with hover tooltip | WI-R-04 | NOT BUILT |
| E3.04 | Table view of the curve | WI-R-04 | PARTIAL — the admin price matrix renders as a table; there is no client-facing curve table |
| E3.05 | Image set in every product section | WI-P-03 | BUILT — `A16`. Items currently carry the placeholder, pending real photographs |

## E.4 — Membership

| # | Behaviour | Work item | State |
|---|---|---|---|
| E4.01 | Factory Plan | WI-M-06 | NOT BUILT |
| E4.02 | Commitment lists with live performance | WI-M-06, WI-M-08 | NOT BUILT |
| E4.03 | Automatic performance credits | WI-M-08 | NOT BUILT |
| E4.04 | Capacity: stats, usage bar, ledger, weighting, fairness | WI-M-07 | PARTIAL — `monti/membership.py` enforces a rolling quota and refuses with an explanation; there is no weighted ledger and no `A27` |

## E.5 — Admin bay

| # | Behaviour | Work item | State |
|---|---|---|---|
| E5.01 | Quote queue and published lists | WI-A-02 | BUILT — time remaining is rendered from the SLA deadline |
| E5.02 | Item name and portal assignment | WI-A-07, WI-K-02 | BUILT — assignment is the registration record; only admin writes it |
| E5.03 | Six cost inputs | WI-A-03 | PARTIAL — inputs are stored, attributed and timestamped in `pricing_inputs`, but the fixed set of six is not defined |
| E5.04 | Three editable strategy rows | WI-A-03 | NOT BUILT |
| E5.05 | Lever definitions and quantity-lever toggle | WI-A-03, WI-R-08 | NOT BUILT |
| E5.06 | Live preview of the member's price | WI-A-03 | NOT BUILT |
| E5.07 | Publish moves the item and unlocks its Decision Room | WI-A-03, WI-K-02 | PARTIAL — publish gates what a member sees and `price_matrices.published_at` enforces it; there is no Decision Room to unlock and republish is not versioned |
| E5.08 | Topbar switches to staff identity | WI-A-01, WI-A-11 | PARTIAL — admin can open a member's portal and the view is marked; the impersonation event is **not** written to the member's security log, which §10.4 requires. The `security_log` table exists and is unused |
| E5.09 | **Master ledger** — three period formats, four search modes, export | **WI-L-01…06** | **BUILT** — `A32`, `A33`, `A35`, `A36` |

## E.6 — Global

| # | Behaviour | Work item | State |
|---|---|---|---|
| E6.01 | Light and dark themes | WI-V-01, WI-V-02 | PARTIAL — both themes are tokenized across all three theme states; the capture matrix and the contrast check `A20` are not built |
| E6.02 | Responsive to phone width | WI-V-02, WI-A-01 | PARTIAL — verified at 320/390/768/1280 with zero horizontal overflow, including all three ledger period views; the full §12.2 matrix and touch capture are not done |
| E6.03 | **Client ledger in the member portal** | **WI-L-07, WI-L-08** | **BUILT** — `A34`; client totals equal the admin ledger filtered to that customer |

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
| BUILT | 8 |
| PARTIAL | 11 |
| NOT BUILT | 15 |
| UNVERIFIABLE HERE | 1 |

The two Appendix E rows this run was for — E5.09 and E6.03, the master ledger
and the client ledger — are both BUILT and checked. The Decision Room tier is
the largest gap, and it is untouched rather than half-done.
