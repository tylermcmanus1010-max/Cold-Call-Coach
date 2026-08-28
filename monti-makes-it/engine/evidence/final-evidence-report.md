# Monti Makes It — evidence report

What was built against the protocol, what it is backed by, and what is not done.
Written to be checked, not believed: every claim below names the artifact or the
command that produces it, and each of those runs without me.

```
cd monti-makes-it/engine
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

SECRET_KEY=test .venv/bin/python tests/smoke.py          # 210 end-to-end checks
.venv/bin/python tests/class_a.py --all                  # 14 Class A checks + proofs
.venv/bin/python tests/evidence.py                       # regenerates this directory
```

---

## 1. Where the run landed

| | |
|---|---|
| Class A checks | 14 written, **14 pass**, **14 proven able to fail** |
| End-to-end checks | 210 pass |
| Punch-list items tracked | 52 — 43 certified, 5 partial, 3 not started, 1 blocked external |
| Ledger | 465 orders backfilled, **0 reconciliation breaks**, three period views agreeing |
| Appendix E rows | 35 mapped — 8 built, 11 partial, 15 not built, 1 unverifiable here |
| Old-brand occurrences | 190 before, **0** after, across source, database and rendered output |
| Fixture rows | 509 inventoried, 509 deleted, **0 orphans** |
| Live clients | 1 — Boars Head, with a published matrix, registrations, a genome, images, a tool and a scope-verified agent |

Class A coverage is reported as *proven* coverage. A check that passes but whose
proof did not catch a deliberate defect is reported UNPROVEN and excluded — §1.6
makes counting an unproven check toward coverage a P0 in itself, and on the first
proof run four of the nine were exactly that.

---

## 2. The nine changes in §0.3

| # | Change | State | Backed by |
|---|---|---|---|
| 1 | Rename to Monti Makes It | Done | `A06`, `brand-inventory.csv` |
| 2 | Ownership language removed | Done | `A06` banned strings; copy rewritten, not patched |
| 3 | Public catalogue with ranges | Done | `A08`, `/catalogue` |
| 4 | Ordering registered, not open | Done | `A07`, three server-side gates |
| 5 | Test and example clients deleted | Done | `A14`, `purge-evidence.md` |
| 6 | First real client: Boars Head | Done | `current-clients.md` |
| 7 | A dedicated agent per client | Done | `A30`, `client_agents` |
| 8 | Tappable image viewer on every item | Built, not captured | `A16`; see §5 |
| 9 | A standing site-improvement agent | Not built | see §5 |
| 10 | Master ledger + client ledger | Done | `A32`–`A36`, `ledger-reconciliation.md` |
| 11 | Appendix E as a build list | Mapped, not confirmed | `prototype-inventory.md`; see §5 |

---

## 3. What the checks actually assert

Each one ships with a proof that removes a real guard, confirms the check names
the resulting defect, and puts the guard back. `class-a-proofs.md` has the
per-check record; the defect each proof introduces is named there.

| id | asserts | the defect its proof introduces |
|---|---|---|
| A05 | tenant isolation on every scoped route and asset URL, 404 not 403 | removes `own_or_404`'s scoping clause |
| A06 | no banned brand or ownership string in source, database, rendered output or a sent email | three defects, one per surface |
| A07 | order gating refused server-side at add-to-cart, order-create and checkout-start | removes each of the three guards in turn |
| A08 | no negotiated price, customer or assignment field in a public response | adds the member's price to the public serializer; prints the owning customer on the public page |
| A11 | an order cannot ship before its review clears, by direct call and by route | removes the guard in `ship_order` |
| A14 | zero fixture rows, zero orphans, no customer without an agent | puts a seeded customer back; writes an orphan line |
| A16 | every item page carries a viewer or an explicit empty state | removes the viewer from the public item page |
| A30 | a client agent's queries cannot reach another customer | drops `customer_id` from the agent's WHERE clause |
| A31 | tooling: four facts, ownership sentence, treatment, 5% threshold | adds a fifth fact; strips the ownership sentence; moves the threshold |
| A32 | one ledger row per money event; reconciles; pending is not revenue | deletes a money event's row; records one payment twice |
| A33 | three period views agreeing, and months rolling into quarters into years | moves the quarter boundary by a second; drops a month bucket |
| A34 | ledger tenancy, and client totals equal to the admin's for them | drops the client scope; adds our fee to the client payload |
| A35 | the export is the screen | adds a column the screen lacks; drops a row |
| A36 | search completeness across all four modes | makes member search miss a row; truncates silently |

### What the proofs found

The proof mechanism is the reason the numbers above are worth anything. Its
first run turned four green checks red:

- **A08** edited a template and missed the result. Jinja caches compiled
  templates and Flask leaves auto-reload off outside debug, so a proof's edit
  was invisible unless an earlier proof happened to rebuild the app first.
  **A16 had been passing on exactly that accident.**
- **A11** was passing its route probe for the wrong reason entirely: `login`
  calls `session.clear()`, which drops the CSRF token, so the probe POST was
  refused by the CSRF check before it ever reached the review gate. A refusal
  is a refusal as far as a status code is concerned.
- **A14** could not write the orphan it needed to detect, because foreign keys
  are re-enabled on every connection the app opens.
- **A31** read the 5% threshold out of the module it was checking. Moving the
  constant moved the check's boundary with it, and everything stayed
  self-consistently wrong.

**A33 joined them on this run.** It checked that each period view's buckets
summed to its own grand total and that every row landed in exactly one bucket.
Both remain true when the quarter view buckets by a clock one second off from
the month view's — same rows, one bucket each, same grand total, filed under the
wrong quarter. The check now adds the months inside each quarter and the
quarters inside each year and compares, which is what §11.5.1 means by the views
agreeing, and it caught the skew immediately.

None of these were visible from the pass column.

---

## 4. Two bugs found in the existing engine

Neither was in scope; both were in the path.

**`LATE_COLUMNS` listed `customers` twice.** It is a dict literal, so the second
entry silently replaced the first and six columns — `membership_status`,
`member_since`, `quote_limit`, `quote_cycle_days`, `membership_note`,
`catalog_tags` — were never added to any database that upgraded in place. Fresh
installs got them from `schema.sql`, which is why it stayed invisible. Merged,
and `migrate()` now asserts that every table swept by the purge has its marker
column, so the same shape of mistake fails at import.

**An open question filed against a genome section that does not exist was
dropped in silence.** `_add_genome` walks the six client-facing sections, so a
question filed under a seventh name was written nowhere — a gap the protocol
requires to be visible, silently disappearing. Now an assertion at import.

---

## 5. What is not done

Stated plainly, because a punch list that only contains finished work is not a
punch list.

**The ledger's third leg.** §11.4.2 requires reconciliation across ledger ↔
order log ↔ **payment provider**. Two of the three are compared, continuously,
with zero breaks. There is no payment-provider connection in this environment,
so the third comparison does not happen — and a reconciliation that omits the
provider cannot catch the case where our records agree with each other and both
disagree with the money. `WI-L-10` is PARTIAL for that reason, not because the
code is unfinished.

**Appendix E could not be confirmed.** The appendix's first instruction is to
open the prototype in session `cse_01B2fEc4ZUQ49QMhmcd672yq` and confirm every
row against what it actually does. That session is not reachable from here. All
35 rows are mapped to work items with a build state, and none is confirmed
against real prototype behaviour. The appendix also makes prototype behaviour
the floor — nothing may ship worse than it demonstrated — and I cannot certify
that against a prototype I cannot see. `prototype-inventory.md` says so at the
top rather than in a footnote.

**Not built at all:**

- **The `SITE-01` standing research agent** (§3.5, change 9). A continuous agent
  whose job is finding how the site becomes more useful is a fleet role, not a
  code change, and nothing in this run stands in for it.
- **The §12.2 screenshot matrix** (`WI-G-01`, `WI-V-02`). Eight viewports, two
  orientations, three zoom levels, pointer and touch. "Nothing is done until it
  has been seen" is §0.2.5, and by that standard every visual claim in this run
  is unevidenced. The image viewer in particular is written mobile-first and
  keyboard-operable, and it has not been *seen* on a phone.
- **The Verified Savings Ledger and Proof Library** (§11.2). The home page no
  longer makes an unsourced savings claim, which is the half that was actively
  wrong. What replaces it points at a ledger that does not exist yet, and §11.2
  is explicit that neither may ship in a partial state that implies more
  evidence than exists — so it is described as what a member gets, not shown.
- **Payment-semantics checks A09/A10/A12** (ACH settlement, webhook replay,
  unsigned events). The engine's existing behaviour looks right — the orders
  email fires on confirmation only, `webhook_log` has a unique index on
  `(provider, event_id)` — but "looks right" is not what §9.3 asks for, and I
  have not driven a `processing` event and asserted zero side effects.
- **The governance apparatus** (Part II): wardens, adversarial certification,
  rotating blind spot-checks, the red team, reviewer telemetry. Excluded by
  agreement at the start of the run. The consequence is real and worth stating:
  nothing here has survived an adversary who was trying to falsify it, and the
  protocol is right that a builder certifying their own work is the weakest
  evidence in the ladder.

**Partial:**

- **Ledger performance at volume** (`WI-L-11`). No budget measured against a
  100× seeded set. The period views walk every row in range in Python rather
  than aggregating in SQL, which is fine at 500 rows and is the first thing that
  will need changing.
- **The Decision Room tier** — the largest Appendix E gap. E1.01 through E1.14
  are almost entirely NOT BUILT, and they are untouched rather than half-done.
  The quantity-slider conflict at E.7 is resolved in the data model (bounds live
  in `price_matrix_cells`, not a constant) but the slider itself does not exist.
- **Admin impersonation mirrored to the member's security log** (E5.08, §10.4).
  Admin can open a member's portal and the view is marked, but the event is not
  written to the member's security log. The `security_log` table exists and is
  unused. This is a P1 by §1.6 and it is open.
- **Agent lifecycle** (`WI-C-04`). `sync_with_membership` implements
  suspend-on-pause, revoke-on-decline and reinstate, but is not yet called from
  every membership transition in `membership.py`.
- **Viewer capture** (`WI-P-04`). Built and operable; unverified on a real
  touch device.
- **Two clean critical-path passes** (`WI-O-11`). The automated suites pass
  twice over, but the 20-step journey in Appendix A.6 has not been walked end
  to end by a person.

**One scope conflict, for the Manager to settle:**

§7.3 requires that any old path with no new equivalent gets "a real page
explaining the rename, not a 404". §1.5 bans the old brand from every surface,
in any casing. A page explaining the rename cannot name the old brand, and one
that does not name it explains nothing. As it happens no route ever carried the
brand — the rename touched no path — so nothing 404s and the conflict is not
blocking. It will be the moment the domain changes, and the two sections cannot
both be satisfied then. Flagged rather than decided.

---

## 6. Honest limits of this evidence

- **A14 runs against a synthetic database.** It proves the purge is total on a
  seeded database and that the checks detect a survivor. It does not prove any
  particular production database is clean; that requires running
  `flask purge-fixtures` there and re-running the check against it.
- **The proofs edit the working tree.** They revert in a `finally` and the
  runner fingerprints the tree before and after, so a proof that crashed
  mid-edit voids the run — but the suite should not be run against a tree with
  uncommitted changes you care about.
- **No adversary.** Every check here was written by the same person who wrote
  the code it checks. That is the failure mode §2.6 exists to prevent, and this
  run does not address it.
