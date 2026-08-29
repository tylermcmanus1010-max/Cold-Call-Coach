# Surface inventory — Phase 1

**Owner** AIM-00 · **Verifier** QA-01 (inventory traversal, D-003) · **Skills** SK-46, SK-43, SK-42
**Frozen at** `f0b0e58bf0660a2d3963b3feacbe615b00a948ec` · branch `claude/protocol-document-website-0uerva`

This is the map every later phase indexes against. It is generated from the running
application and the working tree, not typed from memory: routes come from `app.url_map`,
tables from `PRAGMA table_info` on a freshly launched database, templates and assets from
the tree, and the render column from real HTTP responses through the app.

Evidence for every claim below is in `protocol/evidence/phase-01/`.

---

## 1. What was frozen

The build under protocol is **`monti-makes-it/engine`** — the deployable Flask + SQLite
application. `monti-makes-it/prototype` is a three-file in-memory demo — two 4,000-line HTML builds and a README — whose README
says *"What it is not: the product. The data is generated, state is in memory, payments
are simulated, and there is no real authentication."* It is inventoried as one surface and
is out of scope for every in-line item.

| | |
|---|---|
| Routes | 76 (excluding `/static`) |
| Templates | 63 screen + 18 email = 81 |
| Python modules | 28 — 27 under `monti/` plus `app.py`, the WSGI entry |
| Database tables | 45 |
| Static assets | 3 — `css/app.css`, `js/image-viewer.js`, and `static/uploads/.gitkeep`, a 0-byte git placeholder |
| CLI commands | 4 — `flask init-db`, `launch`, `purge-fixtures`, `seed`, read from `app.cli.commands` |
| Schema file | 1 — `monti/schema.sql` |
| Document artifacts | 5 |
| The prototype | 3 files — `monti-prototype.html`, `monti-makes-it-site.html`, `README.md` |
| **Rows in the census** | **281** |
| **Distinct surfaces** | **276** — the 5 document rows are each served by a route already counted, and carry `duplicate_of` |

---

## 2. Method, and two places the method was wrong

Two probes in this inventory returned a wrong answer before returning the right one, and
both are recorded rather than quietly corrected — a grep that finds nothing is not
evidence of absence, and this document is what twenty later phases index against.

**The render census signed itself out.** The first sweep walked routes in sorted order,
which put `GET /logout` before every `/portal/*` route. Every portal row after it read as
anonymous — 302 across the board, which looks exactly like a gating defect and is not one.
Session-mutating routes (`/logout`, `/admin/clients/<id>/open`, `/admin/clients/close`,
`/login`) are now held out of the sweep and probed separately, and the held-out probes are
the CHG-017 baseline.

**The share bars were found by the wrong name.** A probe searching for class names
containing `share` or `bar` reported the share bars absent from the revenue screen. They
are there; they are called `.meter`. The corrected structural method — enumerate every
element that draws a mark, whatever it is called — is what found them, and is what
established that the sparkline genuinely is absent.

**The share-bar probe's twin, which went unreconciled.** The same held-out probe that
became the CHG-017 baseline reported *"view marked in the page: False"* — it searched for
`view_as` / `Viewing as` and the banner says *"Admin view · you are looking at …"*. The
impersonation baseline recorded the right answer; `render-census.txt` kept the wrong one,
and two files in the same evidence pack contradicted each other until QA-01 read them
both.

Where a probe and the build disagreed, the build won.

### 2a. QA-01 failed this phase on its first submission

The gate was called FAIL on clauses 1 and 3, and RES-01 reproduced every material finding
before accepting it (§13.3 move 1). What was wrong:

| | |
|---|---|
| **Clause 1** | The census had six kinds and omitted **Python modules**, **CLI commands** and **the prototype** — while §4 mapped six items onto module paths, CHG-003's only guard lives in `flask launch`, and §1 claimed the prototype was inventoried. Items were mapped to things the "complete" census did not contain. |
| **Clause 3** | `surfaces.tsv` had no item column and contained the string `CHG` zero times, so neither reading of "no surface is unmapped" was answerable from the evidence. The only mapping in existence was prose. |

Fourteen factual errors came with it, and all fourteen reproduced. The ones that mattered:

- **`document-baseline.txt` said no `UPDATE` touches `ledger_entries`.** Two do, at
  `ledger.py:147` and `:159`. The probe's regex was `(UPDATE|DELETE)\s+FROM?\s*(…)`,
  which reads as UPDATE, whitespace, then the literal `FRO` with an optional `M` — it
  could never match. That broken probe was the stated basis for an SK-30 clause, and
  SK-30 is non-waivable.
- **The total was 210 and 5 of those rows were duplicates** of routes already counted.
- **`flash()` came out 85 across 3 modules.** It is 90 across 4; `public.py` was missed
  entirely and the other three were each one short.
- **The 90 email text nodes were presented as additional to the 1,181.** They are inside
  it.
- **"Sign out renders exactly once on all 56 surfaces"** overstated a true narrower
  claim; 11 surfaces do not load the shell at all.
- Smaller miscounts in CHG-004's route and template counts, CHG-005's `.meter` count,
  CHG-011's `/ 100` count, the third static asset (a 0-byte `.gitkeep`, counted but not
  named), and `fixture-probe.txt`'s user count, which included a user the operator
  created rather than one `flask launch` produced.

Every one is corrected in place with the correction marked, rather than silently
overwritten. §1.10's rule is about not reporting a partial pass as a pass; the same logic
says a corrected artifact should show what it was corrected from.

---

## 3. The surface census

Full list: `evidence/phase-01/surfaces.tsv` — 281 rows, six columns:
`kind · surface · detail · area · duplicate_of · items`.

| Kind | Count | Where enumerated from |
|---|---|---|
| route | 76 | `app.url_map` |
| template | 63 | tree |
| email | 18 | `monti/templates/email/` |
| module | 44 | every `.py` in the engine — `monti/`, `tests/` and `app.py`. The first two censuses took `monti/` plus `app.py` and left `tests/` out, while `document-baseline.txt` scores CHG-014 clauses against `tests/`. QA-01 failed clause 1 on that same shape three times; the generator now walks the tree instead of naming the parts |
| config | 6 | the engine's packaging and dotfiles, including `requirements.txt`, which a CHG-014 clause is scored against |
| engine-evidence | 11 | `engine/evidence/` — the pre-protocol artifacts |
| doc | 2 | `PROTOCOL.md`, `START-HERE.md` |
| schema | 1 | `monti/schema.sql` — added after QA-01's second failure |
| table | 45 | `PRAGMA table_info` on a launched database |
| static | 3 | `monti/static/` |
| cli | 4 | read from `app.cli.commands`. The first two versions typed the list by hand and missed `init-db`, which is exactly the failure mode a generated census is supposed to remove |
| document | 5 | each marked `duplicate_of` the route that serves it |
| prototype | 3 | globbed from `../prototype/`. §1 claimed it was inventoried when it was not, then claimed one file when there are three |

**Rendered:** 56 GET surfaces swept as anonymous, as the member and as admin; 41 return
200 for at least one viewer. Full matrix in `evidence/phase-01/render-census.txt`.

---

## 4. The 15 in-line items, each on a named surface

Every item maps to at least one surface. The **state** column is what the frozen build
actually does, measured, not assumed — and for three items it is not what §2.1 describes.

| ID | Primary surface | Also touches | State on the frozen build |
|---|---|---|---|
| CHG-001 | `GET /admin/revenue` · `admin/revenue.html:36-69` | `monti/static/css/app.css`, `monti/analytics.py:77-83` | **Present, with two independent causes.** *(a) Colour.* Every class the chart uses — `.chart-wrap`, `.chart-svg`, `.chart-grid`, `.chart-axis`, `.chart-bar` — is **undefined in app.css**, the only stylesheet either shell loads. Measured in Chromium: `rect.chart-bar` computes to `fill: rgb(0,0,0)`; the grid computes to `stroke: none`. Bars paint black because SVG's default fill is black. Give them real heights and that is the solid black block. Root cause is a stylesheet naming mismatch, **not the fill path VIZ-01's charter diagnoses (D-027)**. *(b) Arithmetic.* **The marks do not sum to the headline, at any period.** `analytics.series()` emits `days` buckets starting from the window's start date, so **today is counted in the total and drawn nowhere** — the gap is 1,911,346 cents at 7d, 21d, 45d, 90d, 180d and 365d alike, identical because it is always the same missing day. The oldest bar is also a partial day drawn as a whole one. **D-031.** |
| CHG-002 | `GET /admin/revenue` (the surface a 30-day trend would live on) | `monti/analytics.py:PERIODS` | **NO SUCH SURFACE.** No `<polyline>` and no `<path>` in any template in the build. `PERIODS` offers 1d/7d/21d/45d/90d/180d/365d — there is no 30-day window either. See §6. |
| CHG-003 | 7 tables carrying `is_fixture` | `monti/purge.py`, `monti/seed.py`, `monti/__init__.py:100` | **Partly remediated.** Zero fixture rows on a fresh launch. But only 7 of 45 tables carry the marker, and the only guard fires at `flask launch`, on `customers` alone. Nothing refuses a fixture row at write time. |
| CHG-004 | 33 `/portal/*` route rows | `monti/templates/portal/` (20 files) | Present as a mandate. The eight sub-items a–h that scope Phases 12, 13 and 14 are **never enumerated in the protocol** (D-019). |
| CHG-005 | `admin/revenue.html`, "Revenue by client" Share column | `monti/static/css/app.css`; `.meter` on 2 more (`admin/order_detail.html`, `portal/quote_detail.html`) | **Present, and it is the same defect as CHG-001.** `.meter` has **no rule in `app.css`** — the file defines `.meter-head`, `.meter-track` and `.meter-fill`, which no template uses. Measured with real rows: `.meter` is `127 × 0` px, background transparent; its `<span>` is `display: inline`, so `width:100%` does nothing, and it is `0 × 0`. The bar is not illegible — it renders nothing. `chg-005-share-bars.png`. |
| CHG-008 | `GET /admin/revenue` | `admin/orders` | **Present.** Marks are not links — no `<a>` wraps a `chart-bar`. No drill-down of any kind. |
| CHG-009 | `GET /admin/revenue`, `GET /admin/ledger`, `GET /portal/ledger` | `analytics.PERIODS`, `ledger.periods` | **Present.** Revenue offers rolling day-windows; both ledgers offer calendar month/quarter/year. Two vocabularies over the same money. |
| CHG-010 | `admin/revenue.html`, Revenue-by-client table | every table with a per-row action | **Present.** `<a class="btn btn-sm" …>Open portal</a>` repeated on every row — exactly the pattern the gate forbids. |
| CHG-011 | Both portals | 132 `|money` uses, 16 `'%.4f'|format`, 30 `/ 100` in templates | **Present.** At least three distinct renderings of currency. |
| CHG-012 | `_shell.html:43` | — | **NOT PRESENT.** Of the 56 swept surfaces, 30 render "Sign out" once, 11 render it zero times (the public pages, the password page and the two CSV exports — none of which loads the shell), and 15 could not be measured because no viewer got a 200. **Zero surfaces render it twice.** See §6c. |
| CHG-013 | `monti/static/css/app.css` | 3 screen templates, 18 email templates | **Present.** 261 hard-coded hex literals in templates: 258 in email, **3 in real screen files** — `portal/requests.html`, `portal/order_detail.html`, `admin/order_detail.html`. SK-07 says zero in any screen file; whether an email template is one is D-019's question. |
| CHG-014 | `monti/ledger.py`, 2 receipt routes | `ledger_entries` | **Half built.** Receipts, numbering and scoped retrieval exist. **No credit note anywhere in code or schema. No PDF library, no `application/pdf`. No byte-identical regeneration path. Admin retrieval unlogged.** |
| CHG-015 | `decision_items`, `item_revisions`, `portal/products.html`, `admin/desk.html` | `item_genome` | Revisions and the Genome exist. Threads, promotion and the notification email are the unbuilt half. |
| CHG-016 | Every screen and email surface | 78 templates, 4 modules | **Unbuilt in full.** No catalogue, no extraction config, no string table, no gettext. 1,181 template text nodes (the 18 email templates contribute 90 of them, not 90 more) and 90 `flash()` messages across 4 modules. No `language` column on `users` or `customers`, and §4.4 requires per-user storage. |
| CHG-017 | `GET /admin/clients/<id>/open` · `admin.py:111` | `security_log` (unwritten), `_shell.html:17` | **Present, and measured.** One GET, no reason prompt, no confirmation. Admin gains a 200 on the full member portal. A banner does render. **Zero rows written to `security_log`, and a POST as the member succeeded** — not read-only, no elevation, no audit. |

---

## 5. "No surface is unmapped"

The phrase admits two readings and the gate does not say which. Filed as **D-033**. Rather
than pick one, the census now answers both from data: `surfaces.tsv` carries an `items`
column naming every in-line item that lands on each surface.

**Reading A — every surface carries an in-line item.** FALSE, and necessarily so: 159 of
the 281 rows carry at least one item and 122 carry none. Fifteen items cannot cover 276
distinct surfaces, and a gate demanding it would be unpassable by construction. The 94
are things like `/webhooks/stripe`, the application routes, `flask init-db`, and 34
tables no in-line item touches.

**The template rules are derived from content; the rest are not, and saying otherwise was
an overclaim.** An earlier revision of this section said *"each rule now opens the file and
looks"*. That is true of the template rules and false of the others, and QA-01 was right to
call it. Precisely:

| Rule set | How it decides |
|---|---|
| templates (63) and email (18) | **reads the file** — CHG-011 is templates that actually render currency, CHG-010 a button inside a table-row loop, CHG-005 `class="meter"`, CHG-016 a visible text node |
| modules (44) | reads the file for `flash(` and `is_fixture`; **matches the path** for analytics / ledger / genome / decisionroom |
| routes (76) | **matches the path** — `/portal`, `/admin/revenue`, `ledger`, `receipt`, `clients/` |
| tables, CLI, static, schema, documents | **hand-typed constants** |

Three known imprecisions QA-01 found and this revision has not fixed, recorded rather than
hidden: CHG-015 matches `admin/crm_detail.html` on the word "revision" in a placeholder;
CHG-014 matches `admin/_base.html` on "receipt" in a sidebar active-class test; CHG-009
matches the two single-receipt routes on the substring "ledger". They are false positives
in the column, not in the register's prose, and tightening them is Phase 2 work rather than
a Phase 1 fix.

**Reading B — every surface in the build appears in the census.** TRUE as of this
revision, and it was not true when QA-01 first read it. The first census had six kinds and
omitted Python modules, CLI commands and the prototype — while §4 mapped six items onto
module paths and §1 claimed the prototype was inventoried. Modules, CLI commands and the
prototype are now rows. The census is generated from `app.url_map`, `PRAGMA table_info`
and the tree, so an omission is a bug in the generator rather than a lapse of attention,
and the generator is `evidence/phase-01/` alongside its output.

Counting honestly: 246 rows, of which 5 document rows are each served by a route already
counted and carry `duplicate_of`. **241 distinct surfaces.**

---

## 6. The findings this phase exists to produce

### 6a. CHG-001 has a second cause that has nothing to do with colour

`analytics.series()` and `analytics.summary()` read the same window and disagree about
it. `_window(days)` returns `(utcnow() - days, utcnow())`, both carrying a time of day.
The SQL sums every PAID order in `[start, end)` — including today. The bucket loop
(`analytics.py:77-83`) then starts at the window's *start date* and emits exactly `days`
calendar buckets, which lands on yesterday.

**Today's revenue is in the headline and has no bar.** Measured on the seeded database:

| period | headline | marks sum | gap |
|---|---|---|---|
| 7d | 15,372,509 | 13,461,163 | **1,911,346** |
| 21d | 44,592,041 | 42,680,695 | **1,911,346** |
| 90d | 168,278,382 | 166,367,036 | **1,911,346** |
| 365d | 536,769,542 | 534,858,196 | **1,911,346** |

The gap is identical at every period because it is always the same missing day. The
oldest bar has the mirror problem: the window opens mid-afternoon, so that bucket holds a
partial day and is drawn the height of a whole one.

CHG-001's gate says *"Marks sum to the headline total."* They do not, anywhere. VIZ-01's
charter says *"A chart that disagrees with the ledger is a P0 regardless of how it
looks"* — this one disagrees with its own headline. **Fixing the stylesheet leaves it
entirely intact.** Filed as **D-031**.

I did not find this. A parallel reader did, and I verified it rather than taking it —
which is the same standard I applied to QA-01 and the same one that caught two of my own
probes.

### 6b. Two items are one layer defect: template class names the stylesheet does not define

Measured, not inferred. `rect.chart-bar` computes to `fill: rgb(0, 0, 0)` in Chromium
because none of `.chart-wrap`, `.chart-svg`, `.chart-grid`, `.chart-axis` or `.chart-bar`
is defined in `monti/static/css/app.css` — and both shells load that file and nothing
else. `app.css` does carry chart rules, at lines 288–300, under a different naming scheme
the template never uses. Brand green is defined at `--green: #1E8F63` and reaches nothing
on this surface.

This changes what Phase 5 is. §4.4's VIZ-01 charter says *"the current defect class is a
fill path closing against the wrong baseline and a y-domain admitting non-numeric
values."* That is not what is wrong. §1.4 says fix the layer, and the layer here is the
contract between the renderer and DS-01's token set — Phase 4's output, consumed at Phase
5. Filed as **D-027**; the charter's diagnosis is not AIM-00's to rewrite.

The same failure hits **CHG-005** on the same surface. `.meter` has no rule either;
`app.css` defines `.meter-head`, `.meter-track` and `.meter-fill`, and no template uses
any of them. Measured with rows to draw: the meter is `127 × 0` px and its `<span>` is
`display: inline`, so the `width:100%` does nothing and it is `0 × 0`. The share bars do
not render at all. That makes CHG-001 and CHG-005 the same defect — which is exactly the
shape §8.1 predicts, *"DS-01 and VIZ-01 doing one job each that closes four items."*
Filed as **D-030**.

And the period picker on the same surface: `.range-row` and `.range-btn` are also
undefined, so `1D 7D 21D 45D 90D 180D 365D` renders as plain text with no border, no
padding and no visible active state. No in-line item covers a control that does not look
like one — CHG-009 covers its vocabulary, CHG-013 its contrast. Filed as **D-032**, not
built (§1.9).

### 6c. §2.1 describes a build state that is not this one

Two of the fifteen items describe a defect that is not present:

- **CHG-002**, *"30-day sparkline is sloppy"* — there is no sparkline in the build, no
  `<polyline>` or `<path>` in any template, and no 30-day window in `analytics.PERIODS`.
- **CHG-012**, *"Sign out appears twice"* — it renders from a single template line
  (`_shell.html:43`) and appears twice on nothing. Precisely: once on 30 of the 56 swept
  surfaces, zero times on 11 that do not load the shell, and unmeasured on 15 that no
  viewer could reach with a 200.

A third, **CHG-003**, is partly remediated: zero fixture rows survive a launch, but the
standing guard the gate requires exists only at `flask launch` and only for one table.

This is not an argument that the items are finished. An item whose defect is absent may
still carry real work — a 30-day trend line may be wanted even though the sloppy one
described does not exist — and deciding that is scope, which is Tyler's under §1.9 and
§12, not AIM-00's. Filed as **D-026**.

What AIM-00 will not do is mark either item closed on its own authority, or quietly
rewrite it to match what is here. Both are recorded as OPEN in the register with their
measured state beside them.

---

## 7. What Phase 2 inherits

Phase 2 is the fixture purge, owned by DATA-01 and verified by DATAOPS-01. From this
inventory it inherits:

- **7 tables carry `is_fixture`**; 38 do not. On those, a fixture row is not nameable, so
  "zero fixture rows at the data layer" is only checkable on 7/45 of the data layer.
- **The guard clause is the gap.** `monti/__init__.py:100` refuses `flask launch` when a
  fixture *customer* exists. Nothing refuses a fixture row at write time on any table.
- **The degraded-surface list** Phase 2 must file is pre-shaped by the render census: 41
  of 56 GET surfaces render 200 today, on a dataset with one client, two catalogue items,
  two decision items and **zero orders and zero ledger entries**. Every money surface is
  already rendering its empty state.
- **Phase 5 depends on this.** CHG-001's gate wants seven distinct daily marks; with zero
  orders there are none. Whether that gate is testable at Phase 5 turns on what Phase 2's
  list says (D-018).

---

## 8. Evidence index

Every number in this pack is re-derivable. `HOW-TO-REPRODUCE.md` gives the commands and
states the patterns the string counts depend on. The first version of this pack shipped
one generator for eight artifacts; QA-01 failed the phase partly on that, and it was
right to — a figure that cannot be re-derived is a claim, not evidence (§1.1).

| File | Probe | What it demonstrates |
|---|---|---|
| `freeze.md` | — | The commit and tree the inventory was taken at |
| `surfaces.tsv` | `surfaces-generator.py` | The canonical census: 246 rows, 241 distinct, with the item mapping in the data |
| `routes.txt` | (from `app.url_map`) | All 76 routes |
| `templates.txt` | (from the tree) | All 81 templates with line counts |
| `render-census.txt` | `render-census-probe.py` | 56 GET surfaces × 3 viewers; sign-out 30 once / 11 zero / 15 unmeasured / **0 twice**; the held-out session probes |
| `chart-census.txt` | `chart-census-probe.py` | Every drawn mark; the undefined chart and meter classes; CHG-001/002/005/008/009 baselines |
| `fixture-probe.txt` | `fixture-probe.py` | CHG-003's three gate clauses; the guard located exactly |
| `document-baseline.txt` | `document-baseline-probe.py` | CHG-014 clause by clause; no credit note, no PDF |
| `string-census.txt` | `string-census-probe.py` | CHG-016 baseline, with the matching patterns printed beside the counts |
| `impersonation-baseline.txt` | `impersonation-probe.py` | CHG-017 measured: zero log rows, and a write that succeeded |
| `chg-001-revenue-full.png` | `computed-style-probe.mjs` | The revenue surface on the launched database |
| `chg-001-revenue-chart.png` | `computed-style-probe.mjs` | The chart at the zero floor |
| `chg-001-chart-with-data.png` | `meter-probe.mjs` | 90 marks, 81 distinct heights, `fill: rgb(0,0,0)` — the black block, seen |
| `chg-005-share-bars.png` | `meter-probe.mjs` | The Share column: percentages and no bar at all, and CHG-010's repeated button in the same table |
| `series-arithmetic.txt` | `series-arithmetic-probe.py` | The marks-vs-headline gap at every period, and the mechanism in `analytics.py:77-83` |

## 9. A note on prior work in this repository

Work done here before the protocol was handed over is **not** credit against any in-line
item. Under §1.1 nothing counts without evidence attached to this register and
countersigned by the named verifier, and every item above is recorded OPEN regardless of
what the code already does. Where the frozen build already satisfies part of a gate, this
inventory says so as a measurement — not as a pass.
