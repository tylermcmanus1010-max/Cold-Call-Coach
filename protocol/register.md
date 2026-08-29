# Change register

Maintained by AIM-00 under SK-46. No work happens outside this register. No item closes
without an evidence link and a verifier countersignature (SK-46).

Seeded at §0.7 step 2 with all 15 in-line items from §2.1. Every acceptance gate below is
**copied verbatim from §9** — per §1.2 these were written before any work starts, and they
are not reworded here.

**Build status:** AUTHORIZATION is `GO`. **Phase 1 is open** and has been through its
gate twice — QA-01 called FAIL both times, on the inventory's completeness and on the
item mapping, and RES-01 has run §13.3 twice. No item below has moved: every one is OPEN
with no evidence, because Phase 1 produces the map, not the fixes.

Phase 1 measured each item's state against the frozen build rather than trusting §2.1's
description of it. Those measurements are in `surface-inventory.md` §4 and are **not**
credit: under §1.1 nothing counts without evidence attached here and countersigned by the
named verifier.

Severity is assigned by AIM-00 (§3) and is carried here exactly as §2.1 states it. Any
change to a P0 or P1 severity is a hard stop for Tyler (§12 step 4, §0.8).

| ID | Item | Sev | Owner | Verifier | Skills | Phase | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| CHG-001 | Revenue chart renders as solid black block | P0 | ADMIN-01 + VIZ-01 | QA-01 | SK-15, SK-20, SK-53 | 5, 8 | OPEN | — |
| CHG-002 | 30-day sparkline is sloppy | P1 | VIZ-01 | A11Y-01 | SK-17, SK-53 | 5 | OPEN | — |
| CHG-003 | Demo/test clients still present | P0 | DATA-01 | DATAOPS-01 | SK-38 | 2 | OPEN | — |
| CHG-004 | Client portal must be more user friendly | P0 | UX-01 | QA-01 | SK-21–SK-28, SK-55, SK-56 | 12, 13, 14, 15 | OPEN | — |
| CHG-005 | Share bars illegible | P1 | DS-01 + VIZ-01 | A11Y-01 | SK-18, SK-08 | 7 | OPEN | — |
| CHG-008 | Chart has no drill-down | P1 | VIZ-01 + ADMIN-01 | LEDGER-01 | SK-19, SK-54 | 9 | OPEN | — |
| CHG-009 | Range picker doesn't match ledger language | P1 | ADMIN-01 | LEDGER-01 | SK-21, SK-54 | 9 | OPEN | — |
| CHG-010 | "Open portal" button weight | P2 | DS-01 | A11Y-01 | SK-12, SK-28 | 8 | OPEN | — |
| CHG-011 | Inconsistent money typography | P2 | DS-01 | QA-01 | SK-09, SK-10 | 6 | OPEN | — |
| CHG-012 | Sign out appears twice | P2 | ADMIN-01 | QA-01 | SK-23 | 8 | OPEN | — |
| CHG-013 | Contrast unchecked; status by colour alone | P1 | DS-01 | A11Y-01 | SK-07, SK-08, SK-13 | 7 | OPEN | — |
| CHG-014 | Exportable PDF receipt + credit notes | P0 | DOC-01 | LEDGER-01 | SK-29, SK-30, SK-31 | 16 | OPEN | — |
| CHG-015 | Questions & decisions threaded on the item | P1 | UX-01 + ADMIN-01 | SEC-01 | SK-51, SK-26, SK-49 | 18 | OPEN | — |
| CHG-016 | Language selection — English + Spanish | P1 | I18N-01 | CONTENT-01 | SK-48, SK-49, SK-22 | 10, 11 | OPEN | — |
| CHG-017 | Admin impersonation has no controls | P1 | ADMIN-01 | SEC-01 | SK-37, SK-52 | 8 | OPEN | — |

---

## Acceptance gates — verbatim from §9

Each gate is the definition of done for its item. The verifier named in §9 is the agent
that calls it, and it is never the agent that built it (§4.2).

Where §9's verifier differs from §2.1's, both are shown and the discrepancy is filed as
**D-004** — it is not resolved here, because resolving it would be AIM-00 rewriting a
pre-written gate, which §1.2 forbids.

### CHG-001 · P0 · Revenue chart renders as solid black block

- **Owner** ADMIN-01 + VIZ-01 · **Verifier (§9)** QA-01 + LEDGER-01 · **Skills** SK-15, SK-20, SK-53 · **Phase** 5
- **Status** OPEN · **Evidence** none

> Seven distinct daily marks. Tallest equals Best Day and sits below axis max. Marks sum to the headline total. Hover returns the correct single day. Correct in both themes. Survives the SK-53 hostile battery.

> **Verifier discrepancy (D-004).** §2.1 names `QA-01`; §9 names `QA-01 + LEDGER-01`.

### CHG-002 · P1 · 30-day sparkline is sloppy

- **Owner** VIZ-01 · **Verifier (§9)** A11Y-01 · **Skills** SK-17, SK-53 · **Phase** 5
- **Status** OPEN · **Evidence** none

> One stroked line, brand green, zero or min baseline. Optional soft fill. No fill-flipping. Endpoint marked. 30-day total reconciles with the master ledger.

### CHG-003 · P0 · Demo/test clients still present

- **Owner** DATA-01 · **Verifier (§9)** DATAOPS-01 · **Skills** SK-38 · **Phase** 2
- **Status** OPEN · **Evidence** none

> No fixture data anywhere at the data layer. Every figure recomputes from real data. CRM, ledger, revenue rollups and portal list all clean. The standing guard fires on a deliberately reintroduced fixture row.

### CHG-004 · P0 · Client portal must be more user friendly

- **Owner** UX-01 · **Verifier (§9)** QA-01 · **Skills** SK-21–SK-28, SK-55, SK-56 · **Phase** 12
- **Status** OPEN · **Evidence** none

> A person who has never seen the portal completes submit-quote, find-my-item, view-image and read-my-ledger unassisted, each under a stated step count, with no dead ends, verified at phone width.

### CHG-005 · P1 · Share bars illegible

- **Owner** DS-01 + VIZ-01 · **Verifier (§9)** A11Y-01 · **Skills** SK-18, SK-08 · **Phase** 7
- **Status** OPEN · **Evidence** none

> A reader ranks all clients correctly from the bars alone with numbers hidden. Track and fill visible in both themes.

### CHG-008 · P1 · Chart has no drill-down

- **Owner** VIZ-01 + ADMIN-01 · **Verifier (§9)** LEDGER-01 · **Skills** SK-19, SK-54 · **Phase** 9
- **Status** OPEN · **Evidence** none

> Any day opens its orders filtered to that date. Drill-down count and sum equal the mark clicked. Back returns to the prior range intact.

### CHG-009 · P1 · Range picker doesn't match ledger language

- **Owner** ADMIN-01 · **Verifier (§9)** LEDGER-01 · **Skills** SK-21, SK-54 · **Phase** 9
- **Status** OPEN · **Evidence** none

> One period vocabulary across revenue, master ledger and client ledger. A period chosen on one surface carries to the others. Totals agree across all three.

### CHG-010 · P2 · "Open portal" button weight

- **Owner** DS-01 · **Verifier (§9)** A11Y-01 · **Skills** SK-12, SK-28 · **Phase** 8
- **Status** OPEN · **Evidence** none

> The row is the primary target with visible hover and focus states, reachable by keyboard. No table anywhere repeats a filled primary button per row.

### CHG-011 · P2 · Inconsistent money typography

- **Owner** DS-01 · **Verifier (§9)** QA-01 · **Skills** SK-09, SK-10 · **Phase** 6
- **Status** OPEN · **Evidence** none

> One documented money style applied to every currency instance in both portals.

### CHG-012 · P2 · Sign out appears twice

- **Owner** ADMIN-01 · **Verifier (§9)** QA-01 · **Skills** SK-23 · **Phase** 8
- **Status** OPEN · **Evidence** none

> Sign out appears exactly once per view.

### CHG-013 · P1 · Contrast unchecked; status by colour alone

- **Owner** DS-01 · **Verifier (§9)** A11Y-01 · **Skills** SK-07, SK-08, SK-13 · **Phase** 7
- **Status** OPEN · **Evidence** none

> Every text and UI pairing meets contrast minimums in both themes. No state distinguishable by hue alone. Palette documented as tokens.

### CHG-014 · P0 · Exportable PDF receipt + credit notes

- **Owner** DOC-01 · **Verifier (§9)** LEDGER-01 · **Skills** SK-29, SK-30, SK-31 · **Phase** 16
- **Status** OPEN · **Evidence** none

> Exactly one receipt per purchase, unbroken immutable numbering. Same receipt regenerates byte-identical from stored order data. Totals reconcile to the order and both ledgers. No code path edits or deletes an issued receipt. Refund test yields original intact + credit note + correct net, both exporting as PDF. Clients retrieve only their own. Admin retrieval logged.

### CHG-015 · P1 · Questions & decisions threaded on the item

- **Owner** UX-01 + ADMIN-01 · **Verifier (§9)** SEC-01 + GENOME-01 + NOTIFY-01 · **Skills** SK-51, SK-26, SK-49 · **Phase** 18
- **Status** OPEN · **Evidence** none

> A promoted decision produces exactly one Product Genome revision; a revision always links back to its source message; neither exists alone. No thread action changes a spec without a revision record. Threads survive rename and reorder. No cross-tenant reachability by any route including direct URL. Every message carries author, role and timestamp. Reordering an item two years on still shows the decision explaining its spec, with date and approver. Notification email carries no spec content. Anchor field present in schema.

> **Verifier discrepancy (D-004).** §2.1 names `SEC-01`; §9 names `SEC-01 + GENOME-01 + NOTIFY-01`.

### CHG-016 · P1 · Language selection — English + Spanish

- **Owner** I18N-01 · **Verifier (§9)** CONTENT-01 + A11Y-01 · **Skills** SK-48, SK-49, SK-22 · **Phase** 10
- **Status** OPEN · **Evidence** none

> Zero hard-coded user-facing literals. Switching language changes every visible string including errors, empty states, validation and email templates. No client-authored content machine-translated anywhere. Layout holds with Spanish strings 20–35% longer, verified at phone width, buttons and nav checked specifically. Currency stays USD. Spanish copy signed off by a named fluent human. Every Phase 12 rename re-checked in Spanish at Phase 12b.

> **Verifier discrepancy (D-004).** §2.1 names `CONTENT-01`; §9 names `CONTENT-01 + A11Y-01`.

### CHG-017 · P1 · Admin impersonation has no controls

- **Owner** ADMIN-01 · **Verifier (§9)** SEC-01 · **Skills** SK-37, SK-52 · **Phase** 8
- **Status** OPEN · **Evidence** none

> In scope per D-001. Every impersonation session logged, timestamped, attributed to a named admin, reason-tagged, read-only by default, and visible in the member's security log within one page load; write actions during impersonation require a separate logged elevation.

---

## Out of scope, kept for the trail

- **CHG-006** margin on the money screen — scrapped 29 Aug by Tyler (§2.2, Appendix C).
- **CHG-007** pending/settling figure — scrapped 29 Aug by Tyler (§2.2, Appendix C).

Both need order-level financial state that does not exist. PRICE-01 and PAY-01 are the
dormant homes for them and activate together or not at all (Appendix C).

