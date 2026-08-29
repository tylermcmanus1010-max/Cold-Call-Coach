# Change register

Maintained by AIM-00 under SK-46. No work happens outside this register. No item closes
without an evidence link and a verifier countersignature (SK-46).

Rebuilt against **Amendment 2**: 14 in line, 1 closed. Every acceptance gate is **copied
verbatim from §9** of the packet — per §1.2 they were written before work starts and are
not reworded here.

**Every item is mapped against the Flask repo (D-028).** The surfaces below come from the
Phase 1 census, `protocol/evidence/phase-01/surfaces.tsv`, which contains no prototype row
for any item. **No item cites the prototype as its evidence surface.** The prototype is
design intent; where a feature is absent from the repo the item is build-to-intent, not
fix-a-defect.

**Build status:** AUTHORIZATION `HOLD`. Phase 1 is open; its gate is being re-called
against this amended register. Any verdict returned against the pre-amendment register is
provisional and does not carry forward (§0.8 step 5).

Severity is assigned by AIM-00 (§3). Any change to a P0 or P1 severity is a hard stop for
Tyler (§12 step 4, §0.9).

| ID | Item | Sev | Owner | Verifier | Skills | Phase | Status | Repo surfaces | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| CHG-001 | Revenue chart renders as solid black block | P0 | ADMIN-01 + VIZ-01 | QA-01 | SK-15, SK-20, SK-53 | 5, 8 | OPEN | `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/static/css/app.css` (+1 more) | — |
| CHG-002 | 30-day sparkline — **absent in the repo; build to prototype intent** (D-026) | P1 | VIZ-01 | A11Y-01 | SK-15, SK-17, SK-53 | 5 | OPEN | `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/analytics.py` | — |
| CHG-003 | Demo/test clients still present | P0 | DATA-01 | DATAOPS-01 | SK-38 | 2 | OPEN | `monti/__init__.py`, `monti/db.py`, `monti/intake.py` (+14 more) | — |
| CHG-004 | Client portal must be more user friendly | P0 | UX-01 | QA-01 | SK-21–SK-28, SK-55, SK-56 | 12, 13, 14, 15 | OPEN | `GET /portal/`, `GET /portal/cart`, `GET /portal/catalog` (+50 more) | — |
| CHG-005 | Share bars illegible | P1 | DS-01 + VIZ-01 | A11Y-01 | SK-18, SK-08 | 7 | OPEN | `GET /admin/revenue`, `monti/templates/admin/order_detail.html`, `monti/templates/admin/revenue.html` (+2 more) | — |
| CHG-008 | Chart has no drill-down | P1 | VIZ-01 + ADMIN-01 | LEDGER-01 | SK-19, SK-54 | 9 | OPEN | `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/analytics.py` | — |
| CHG-009 | Range picker doesn't match ledger language | P1 | ADMIN-01 | LEDGER-01 | SK-21, SK-54 | 9 | OPEN | `GET /admin/ledger`, `GET /admin/ledger/export.csv`, `GET /admin/ledger/receipt/<receipt_no>` (+9 more) | — |
| CHG-010 | "Open portal" button weight | P2 | DS-01 | A11Y-01 | SK-12, SK-28 | 8 | OPEN | `GET /admin/revenue`, `monti/templates/_ledger.html`, `monti/templates/admin/catalog.html` (+16 more) | — |
| CHG-011 | Inconsistent money typography | P2 | DS-01 | QA-01 | SK-09, SK-10 | 6 | OPEN | `monti/templates/_ledger.html`, `monti/templates/admin/application_detail.html`, `monti/templates/admin/catalog.html` (+31 more) | — |
| CHG-012 | Sign out appears twice | — | — | QA-01 | SK-23 | 8 | **CLOSED** | `monti/templates/_shell.html` | `evidence/phase-01/render-census.txt` |
| CHG-013 | Contrast unchecked; status by colour alone | P1 | DS-01 | A11Y-01 | SK-07, SK-08, SK-13 | 7 | OPEN | `monti/templates/admin/catalog.html`, `monti/templates/admin/catalog_detail.html`, `monti/templates/admin/crm.html` (+42 more) | — |
| CHG-014 | Exportable PDF receipt + credit notes | P0 | DOC-01 | LEDGER-01 | SK-29, SK-30, SK-31 | 16 | OPEN | `GET /admin/ledger/receipt/<receipt_no>`, `GET /portal/ledger/receipt/<receipt_no>`, `monti/templates/_ledger.html` (+11 more) | — |
| CHG-015 | Questions & decisions threaded on the item | P1 | UX-01 + ADMIN-01 | SEC-01 | SK-51, SK-26, SK-49 | 18 | OPEN | `monti/templates/admin/crm_detail.html`, `monti/templates/portal/genome.html`, `monti/decisionroom.py` (+5 more) | — |
| CHG-016 | Language selection — English + Spanish | P1 | I18N-01 | CONTENT-01 | SK-48, SK-49, SK-22 | 10, 11 | OPEN | `monti/templates/_image_viewer.html`, `monti/templates/_ledger.html`, `monti/templates/_shell.html` (+81 more) | — |
| CHG-017 | Admin impersonation has no controls | P1 | ADMIN-01 | SEC-01 | SK-37, SK-52 | 8 | OPEN | `GET /admin/clients/<int:customer_id>/open`, `GET /admin/clients/close`, `monti/templates/_shell.html` (+5 more) | — |

**14 in line · 1 closed.** Every in-line item carries at least one
repo surface from the Phase 1 census; surface counts per item are in `surfaces.tsv`.

---

## Acceptance gates — verbatim from §9 of Amendment 2

### CHG-001 · P0 · Revenue chart renders as solid black block

- **Owner** ADMIN-01 + VIZ-01 · **Verifier** QA-01 + LEDGER-01 · **Skills** SK-15, SK-20, SK-53 · **Phase** 5
- **Status** OPEN
- **Repo surfaces (4)** `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/static/css/app.css` (+1 more)
- **Evidence** none

> Seven distinct daily marks. Tallest equals Best Day and sits below axis max. Marks sum to the headline total. Hover returns the correct single day. Correct in both themes. Survives the SK-53 hostile battery.

### CHG-002 · P1 · 30-day sparkline

- **Owner** VIZ-01 · **Verifier** A11Y-01 · **Skills** SK-15, SK-17, SK-53 · **Phase** 5
- **Status** OPEN
- **Repo surfaces (3)** `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/analytics.py`
- **Evidence** none

> Build-to-intent per D-026 and D-028; the sparkline does not exist in the repo. The gate therefore requires, in addition: a 30-day window exists in `analytics.PERIODS`, and the sparkline renders on the surface Phase 1 mapped it to. Then, as originally written — one stroked line, brand green, zero or min baseline, optional soft fill, no fill-flipping, endpoint marked, and the 30-day total reconciles with the master ledger.

### CHG-003 · P0 · Demo/test clients still present

- **Owner** DATA-01 · **Verifier** DATAOPS-01 · **Skills** SK-38 · **Phase** 2
- **Status** OPEN
- **Repo surfaces (17)** `monti/__init__.py`, `monti/db.py`, `monti/intake.py` (+14 more)
- **Evidence** none

> No fixture data anywhere at the data layer. Every figure recomputes from real data. CRM, ledger, revenue rollups and portal list all clean. The standing guard fires on a deliberately reintroduced fixture row.

### CHG-004 · P0 · Client portal must be more user friendly

- **Owner** UX-01 · **Verifier** QA-01 · **Skills** SK-21–SK-28, SK-55, SK-56 · **Phase** 12
- **Status** OPEN
- **Repo surfaces (53)** `GET /portal/`, `GET /portal/cart`, `GET /portal/catalog` (+50 more)
- **Evidence** none

> A person who has never seen the portal completes submit-quote, find-my-item, view-image and read-my-ledger unassisted, each under a stated step count, with no dead ends, verified at phone width.

### CHG-005 · P1 · Share bars illegible

- **Owner** DS-01 + VIZ-01 · **Verifier** A11Y-01 · **Skills** SK-18, SK-08 · **Phase** 7
- **Status** OPEN
- **Repo surfaces (5)** `GET /admin/revenue`, `monti/templates/admin/order_detail.html`, `monti/templates/admin/revenue.html` (+2 more)
- **Evidence** none

> A reader ranks all clients correctly from the bars alone with numbers hidden. Track and fill visible in both themes.

### CHG-008 · P1 · Chart has no drill-down

- **Owner** VIZ-01 + ADMIN-01 · **Verifier** LEDGER-01 · **Skills** SK-19, SK-54 · **Phase** 9
- **Status** OPEN
- **Repo surfaces (3)** `GET /admin/revenue`, `monti/templates/admin/revenue.html`, `monti/analytics.py`
- **Evidence** none

> Any day opens its orders filtered to that date. Drill-down count and sum equal the mark clicked. Back returns to the prior range intact.

### CHG-009 · P1 · Range picker doesn't match ledger language

- **Owner** ADMIN-01 · **Verifier** LEDGER-01 · **Skills** SK-21, SK-54 · **Phase** 9
- **Status** OPEN
- **Repo surfaces (12)** `GET /admin/ledger`, `GET /admin/ledger/export.csv`, `GET /admin/ledger/receipt/<receipt_no>` (+9 more)
- **Evidence** none

> One period vocabulary across revenue, master ledger and client ledger. A period chosen on one surface carries to the others. Totals agree across all three.

### CHG-010 · P2 · "Open portal" button weight

- **Owner** DS-01 · **Verifier** A11Y-01 · **Skills** SK-12, SK-28 · **Phase** 8
- **Status** OPEN
- **Repo surfaces (19)** `GET /admin/revenue`, `monti/templates/_ledger.html`, `monti/templates/admin/catalog.html` (+16 more)
- **Evidence** none

> The row is the primary target with visible hover and focus states, reachable by keyboard. No table anywhere repeats a filled primary button per row.

### CHG-011 · P2 · Inconsistent money typography

- **Owner** DS-01 · **Verifier** QA-01 · **Skills** SK-09, SK-10 · **Phase** 6
- **Status** OPEN
- **Repo surfaces (34)** `monti/templates/_ledger.html`, `monti/templates/admin/application_detail.html`, `monti/templates/admin/catalog.html` (+31 more)
- **Evidence** none

> One documented money style applied to every currency instance in both portals.

### CHG-012 · closed · Sign out appears twice

- **Owner** — · **Verifier** QA-01 · **Skills** SK-23 · **Phase** 8
- **Status** **CLOSED** — 29 Aug 2026 by D-026
- **Repo surfaces (1)** `monti/templates/_shell.html`
- **Evidence** `evidence/phase-01/render-census.txt` — 56 surfaces swept, sign out renders once on 30, zero on 11 that do not load the shell, unmeasured on 15, **twice on none**. Countersigned by QA-01.

> **CLOSED 29 Aug 2026 by D-026, verified absent.** Sign out renders exactly once across all 56 swept surfaces; the render census is the evidence, countersigned by QA-01. Retained for the trail. Any later view that renders it twice reopens this ID rather than opening a new one.

### CHG-013 · P1 · Contrast unchecked; status by colour alone

- **Owner** DS-01 · **Verifier** A11Y-01 · **Skills** SK-07, SK-08, SK-13 · **Phase** 7
- **Status** OPEN
- **Repo surfaces (45)** `monti/templates/admin/catalog.html`, `monti/templates/admin/catalog_detail.html`, `monti/templates/admin/crm.html` (+42 more)
- **Evidence** none

> Every text and UI pairing meets contrast minimums in both themes. No state distinguishable by hue alone. Palette documented as tokens.

### CHG-014 · P0 · Exportable PDF receipt + credit notes

- **Owner** DOC-01 · **Verifier** LEDGER-01 · **Skills** SK-29, SK-30, SK-31 · **Phase** 16
- **Status** OPEN
- **Repo surfaces (14)** `GET /admin/ledger/receipt/<receipt_no>`, `GET /portal/ledger/receipt/<receipt_no>`, `monti/templates/_ledger.html` (+11 more)
- **Evidence** none

> Exactly one receipt per purchase, unbroken immutable numbering. Same receipt regenerates byte-identical from stored order data. Totals reconcile to the order and both ledgers. No code path edits or deletes an issued receipt. Refund test yields original intact + credit note + correct net, both exporting as PDF. Clients retrieve only their own. Admin retrieval logged.

### CHG-015 · P1 · Questions & decisions threaded on the item

- **Owner** UX-01 + ADMIN-01 · **Verifier** SEC-01 + GENOME-01 + NOTIFY-01 · **Skills** SK-51, SK-26, SK-49 · **Phase** 18
- **Status** OPEN
- **Repo surfaces (8)** `monti/templates/admin/crm_detail.html`, `monti/templates/portal/genome.html`, `monti/decisionroom.py` (+5 more)
- **Evidence** none

> A promoted decision produces exactly one Product Genome revision; a revision always links back to its source message; neither exists alone. No thread action changes a spec without a revision record. Threads survive rename and reorder. No cross-tenant reachability by any route including direct URL. Every message carries author, role and timestamp. Reordering an item two years on still shows the decision explaining its spec, with date and approver. Notification email carries no spec content. Anchor field present in schema.

### CHG-016 · P1 · Language selection

- **Owner** I18N-01 · **Verifier** CONTENT-01 + A11Y-01 · **Skills** SK-48, SK-49, SK-22 · **Phase** 10
- **Status** OPEN
- **Repo surfaces (84)** `monti/templates/_image_viewer.html`, `monti/templates/_ledger.html`, `monti/templates/_shell.html` (+81 more)
- **Evidence** none

> Zero hard-coded user-facing literals. Switching language changes every visible string including errors, empty states, validation and email templates. No client-authored content machine-translated anywhere. Layout holds with Spanish strings 20–35% longer, verified at phone width, buttons and nav checked specifically. Currency stays USD. Spanish copy signed off by a named fluent human. Every Phase 12 rename re-checked in Spanish at Phase 12b.

### CHG-017 · P1 · Admin impersonation has no controls

- **Owner** ADMIN-01 · **Verifier** SEC-01 · **Skills** SK-37, SK-52 · **Phase** 8
- **Status** OPEN
- **Repo surfaces (8)** `GET /admin/clients/<int:customer_id>/open`, `GET /admin/clients/close`, `monti/templates/_shell.html` (+5 more)
- **Evidence** none

> In scope per D-001. Every impersonation session logged, timestamped, attributed to a named admin, reason-tagged, read-only by default, and visible in the member's security log within one page load; write actions during impersonation require a separate logged elevation. **Cross-cutting** — Tenant isolation verified adversarially by SEC-01 (Phase 19). Every surface renders correctly with the real post-purge dataset (Phase 14). All money surfaces reconcile four ways (Phase 17). A restore drill completed within the cycle (SK-41, §11.2). ---

---

## Out of scope, kept for the trail

- **CHG-006** margin on the money screen — scrapped 29 Aug by Tyler (§2.2, Appendix C).
- **CHG-007** pending/settling figure — scrapped 29 Aug by Tyler (§2.2, Appendix C).

Both need order-level financial state that does not exist. PRICE-01 and PAY-01 are the
dormant homes for them and activate together or not at all (Appendix C).

## Diagnoses attached to items, sourced to evidence (§4.8, D-027)

Charter notes may not assert a cause. These are the causes Phase 1 measured, and they
live here rather than in any charter.

| Item | Measured cause | Evidence |
|---|---|---|
| CHG-001 | *(a)* Every chart class is undefined in `app.css`, the only stylesheet either shell loads, so `rect.chart-bar` computes to `fill: rgb(0,0,0)`. *(b)* `analytics.series()` emits its buckets from the window's start date while `summary()` includes today, so the marks never sum to the headline — a gap of 1,911,346 cents at every period. | `chart-census.txt`, `series-arithmetic.txt`, `chg-001-chart-with-data.png` |
| CHG-005 | `.meter` has no rule in `app.css`; the file defines `.meter-head`/`.meter-track`/`.meter-fill`, which no template uses. Measured: the bar is `127 × 0` px and its span is `display:inline` at `0 × 0`. It renders nothing. | `chart-census.txt`, `chg-005-share-bars.png` |
| CHG-002 | Absent from the repo — no `<polyline>`, no `<path>`, no 30-day window in `analytics.PERIODS`. Build-to-intent per D-026 and D-028. | `chart-census.txt` |
| CHG-003 | Zero fixture rows after launch, but only 7 of 45 tables carry the marker and the only guard fires at `flask launch`, on `customers` alone. | `fixture-probe.txt` |
| CHG-014 | No credit note in code or schema; no PDF library; no byte-identical regeneration path; admin retrieval unlogged. | `document-baseline.txt` |
| CHG-016 | No catalogue, no extraction config, no string table, no `language` column. 1,181 template text nodes across 78 files and 90 `flash()` messages across 4 modules. | `string-census.txt` |
| CHG-017 | One GET, no reason prompt, no confirmation. A write as the member succeeded and `security_log` stayed at zero rows. | `impersonation-baseline.txt` |

