# Decisions, waivers and overrides

Every decision, waiver and override, with who signed it, when, and its expiry. A waiver
with no signature, no named owner or no expiry does not exist (§13.4).

Amendments are not waivers. D-001, D-002 and D-003 are amendments: each changes the
protocol, none weakens a §1 directive, and none carries an expiry.

**Standing rule (§0.9):** every contradiction AIM-00 finds is filed here with the real
options, the cost of each, and a recommendation. AIM-00 never amends the protocol itself,
and never recommends the option that carves an exception into a §1 directive or into
§13.4. Where that looks like the only way through, *that is the finding*, and it goes to
Tyler. **D-016 is the live example.**

---

# PART 1 — ANSWERED

## D-001 · §4.6, admin impersonation (OPEN-A) · **MOVED IN**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** Move OPEN-A into scope, or leave it in Appendix B?

**Answer.** Moved in. OPEN-A leaves Appendix B and enters §2.1 as **CHG-017** — P1, owner
ADMIN-01, verifier SEC-01, skills SK-37 + SK-52, placed in Phase 8 alongside CHG-010.

**Applied at:** §2.1 gains the CHG-017 row · §9's gate is no longer conditional · SK-37
moves DORMANT → ACTIVE in §6 Family F · SK-37 leaves Appendix E's dormant list, which is
now nine skills, not ten · SEC-01's charter no longer "holds SK-37 dormant" · ADMIN-01's
"must not implement impersonation controls" restriction is lifted, **that one clause only**
· Phase 8 gains CHG-017, SK-37, SK-52 and SEC-01 as a third verifier · Appendix B/OPEN-A
is marked resolved · §11's "§4.6 answered and recorded" line is satisfied.

**ADMIN-01 does not verify its own impersonation controls. SEC-01 does.** §4.2 applies here
as everywhere, and this is the item where it matters most.

**Side effect worth recording.** CHG-014's gate requires *"Admin retrieval logged."* The
only catalogue skill that logs admin access to a client's records is SK-37, which was
DORMANT. Under the declined answer, CHG-014 would have carried a clause with no active
skill behind it. D-001 closed that hole as well as its own.

---

## D-002 · §11.2, SK-41 restore drill · **ACCEPTED**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** Accept the proposed go/no-go line, or decline it?

**Answer.** Accepted. A standing go/no-go line, not a proposal. SK-41 is ACTIVE.

**A drill means an actual restore, actually timed, inside the cycle. A backup job that ran
is not evidence** (§0.2, SK-41's acceptance gate).

**Applied at:** §11 carries the line — the list is now sixteen · SK-41 stays ACTIVE in §6
Family F · §9's cross-cutting clause stands · DATAOPS-01's gate keeps its restore-drill
clause · Appendix E keeps SK-41 in the Continuous row.

**Note.** "Within the current cycle" is now load-bearing for a launch gate, and *cycle* is
nowhere defined. Filed as **D-020**.

---

## D-003 · Phase 1 had no one permitted to call its gate · **RESOLVED by changing the verifier**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** §7 and Appendix E named RES-01 as Phase 1's verifier. §13.4 says RES-01
*"may not call a gate at all ... is neither owner nor verifier of anything."* §4.2 forbids
the owner (AIM-00) calling its own. Nobody could call the first gate of the build.

**Answer.** **Phase 1's verifier is QA-01.** §13.4 is unamended and absolute: **RES-01
never calls a gate, anywhere, with no exceptions.**

**Why this shape and not the other.** Two fixes were available. Excepting Phase 1 inside
§13.4 would have carved the first hole in the one clause that keeps RES-01 from grading its
own unblocking, and a rule with one exception is a rule with a precedent. Changing the
verifier fixes the same contradiction and costs nothing later. QA-01 is right on the merits
rather than by elimination: it owns no in-line item, and confirming that every surface is
mapped and every in-line item lands on a named surface is a traversal of the inventory,
which is SK-43's shape exactly.

**RES-01 stays subscribed to Phase 1 as to every phase.** If the gate FAILs, it wakes. It
simply does not call the gate.

**Applied at:** §7 Phase 1 verifier line · Phase 1's skills gain SK-43 · Appendix E row 1 ·
Appendix F gains a Phase-1-verifier row.

---

## D-026 · CHG-002 and CHG-012 · **SPLIT**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** Phase 1 measured two in-line items whose stated defect is absent from the
build. Are they finished, or is the work something else?

**Answer.** Split, and neither is "finished".

- **CHG-012 — CLOSED, verified absent.** Sign out renders exactly once across all 56
  swept surfaces. The render census is the evidence, countersigned by QA-01. It stays in
  the register as CLOSED, never deleted. **Any later view that renders it twice reopens
  this ID rather than opening a new one.**
- **CHG-002 — stays OPEN, rewritten.** There is no sparkline, no `<polyline>` or `<path>`
  in any template, and no 30-day window in `analytics.PERIODS`. A sparkline was seen on
  the prototype, so the work is build-it-correctly, not fix-it. Its §9 gate gains the
  build conditions. Severity unchanged at P1.

**The rule it sets:** *an absent defect is not finished work.* Closing an item is a scope
decision and belongs to Tyler under §12, never to the agent that found it.

**Applied at:** §2.1 — CHG-002's row rewritten, skills now SK-15/SK-17/SK-53; CHG-012's
row marked CLOSED with no owner and no severity · §9 — both gates rewritten · the register
is now 14 in line, 1 closed.

---

## D-027 · §4.4's VIZ-01 charter asserted a cause measurement contradicts · **CORRECTED**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** The charter said CHG-001's defect was *"a fill path closing against the
wrong baseline and a y-domain admitting non-numeric values."* Measured in Chromium at
Phase 1 it is neither: every chart class is undefined in `app.css`, so the bars take
SVG's default black fill. Correct the charter, or correct the practice?

**Answer.** Both. The charter is corrected in §4.4, and **§4.8 now forbids any charter
note from asserting a cause at all.**

**The reasoning is the part worth keeping.** That sentence came from v1.0 and was carried
into v2.0 verbatim without being tested — the merge preserved it faithfully, which is
precisely how a wrong diagnosis survives a revision. A diagnosis inside a charter is
worse than no diagnosis, because it reads as settled and survives every revision
unchallenged. It would have sent VIZ-01 into the renderer while the fault sat in a
stylesheet, with the authority of the protocol behind it.

**Standing rule (§4.8):** a charter note may state a principle, a standard, a prohibition
or a scope boundary. It may not say what is wrong with the code. Diagnoses belong in the
register — attached to an item, sourced to evidence, dated, falsifiable. **Any charter
note that asserts a cause is itself a finding.**

---

## D-028 · The change register was written against the prototype · **THE FLASK REPO IS THE BUILD OF RECORD**

**Signed:** Tyler · **Date:** 29 Aug 2026 · **Expiry:** none — this is an amendment.

**Question.** Phase 1 found CHG-002 and CHG-012 describe defects the repo does not have.
Two bad items, or something structural?

**Answer.** Structural. The 16 change items were logged against the claude.ai prototype
surface, and the repo is a different codebase. It is a register-provenance problem, not a
two-item problem — and Phase 1's mapping gate is exactly where it should surface.

**The repo is what ships. The prototype becomes the design reference.** Every in-line item
is re-mapped against the repo, and where a prototype feature is simply absent, the item is
rewritten from *fix-a-defect* to *build-to-intent* with a gate that says so. This makes
the work larger and the register honest; the alternative was building against a surface
nobody is shipping.

**Standing consequence: no item may cite the prototype as its evidence surface.**
Prototype behaviour is intent, never a baseline.

**AIM-00 note.** Phase 1's inventory already treated the engine as the build under
protocol and recorded the prototype as one out-of-scope surface, so nothing in the
evidence pack cites it. What changes is the framing of the absences: they were reported
as "the protocol describes a build state that is not this one", which named the symptom.
D-028 names the cause.

---

## D-029 · The Phase 1 impersonation test wrote a record as Boars Head · **REVERT IT, AND NO TEST LEAVES RESIDUE AGAIN**

**Raised in review, not by the build.** **Signed:** Tyler · **Date:** 29 Aug 2026 ·
**Expiry:** none — this is an amendment.

**Question.** Phase 1's CHG-017 baseline was established by impersonating Boars Head and
writing a record as them. Correct test, correct finding — `security_log` stayed at zero
rows, so impersonation is not read-only, has no elevation step and no audit. But the
written record was not reported as removed, and Boars Head is the only real client in the
system.

**Answer.** Locate and revert it, evidence the revert, and add the no-residue rule to
SEC-01's charter (§4.5): **every write performed while testing is reverted in the same
phase, and a test that must write uses a throwaway account, never MMI-C-1001.**

**Executed — and it was worse than the decision assumed.** Evidence:
`protocol/evidence/phase-01/d029-revert.txt`, probe `d029-revert-probe.py`.

`monti/intake.py:create_request` writes **five** rows per submission. The Phase 1 probe's
own cleanup deleted three of them — the quote, the product and the capacity debit — and
**missed the CRM activity and the calendar deadline**, then printed *"(probe rows
removed)"*. That line was in the evidence pack and it was false.

Found and reverted: **12 rows across four databases**, of which **8 sat on Boars Head's own
account** — 2 CRM activities and 2 calendar deadlines in each of the two launched
databases. Boars Head's CRM timeline had three entries where it should have had one.

Re-proved by fresh query after the revert, not asserted: all five markers return **0
rows**, and the timeline is back to its single genuine entry, *"Account opened as the
first client on the platform."* His two real products, MMI-D-001 and MMI-D-002, are
untouched.

**What the first probe got wrong, stated plainly:** it searched for its own text marker
only. The calendar row carries neither the marker nor the item reference — only the quote
reference — so a search by marker could never have found it. A search that finds nothing
is not proof that nothing is there if the search was too narrow. The shipped probe now
searches by marker *and* by both generated references.


# PART 2 — FILED BY AIM-00, UNANSWERED

> **ID collision, resolved and recorded.** AIM-00 had already filed findings under D-026
> to D-029 at Phase 1. Amendment 2 assigns those four numbers to Tyler's signed decisions.
> Two of the four are the same subject and merge cleanly — the agent's D-026 (two items
> whose defect is absent) and D-027 (the VIZ-01 charter's wrong cause) are the findings
> Tyler's D-026 and D-027 answer. **Two collide on different subjects:** the agent's D-028
> (the unstyled period picker) and D-029 (the ambiguous gate clause) are unrelated to
> Tyler's D-028 and D-029.
>
> Resolved by precedence: a signed decision keeps its number, an unsigned agent finding
> moves. The agent's D-028 is now **D-032** and its D-029 is now **D-033**, both with a
> note recording the move. Nothing is deleted and no number is reused. References in
> `surface-inventory.md` and `phase-board.md` are updated to match.
>
> AIM-00 did not decide this so much as apply the only ordering that loses nothing —
> but it is a change to the record, so it is stated here rather than done quietly.

Twenty-two findings, each verified against the amended text rather than asserted. They are
ordered by the phase they first bite at. None is resolved here; §0.9 forbids AIM-00
amending the protocol itself.

Where several instances share one cause they are filed as one item with the instances
listed, rather than as near-identical duplicates.

---

## D-004 · §2.1 and §9 name different verifiers for three items · **bites at Phase 1**

Verified. Three of the fifteen items have two different verifier sets:

| Item | §2.1 says | §9 says |
|---|---|---|
| CHG-001 (P0) | QA-01 | QA-01 + LEDGER-01 |
| CHG-015 (P1) | SEC-01 | SEC-01 + GENOME-01 + NOTIFY-01 |
| CHG-016 (P1) | CONTENT-01 | CONTENT-01 + A11Y-01 |

It bites at Phase 1 because the register is seeded now and §1.2 forbids rewording a
pre-written gate afterwards. It bites hardest at close: an item closed on one
countersignature when the gate names three has not passed the gate as written.

**Options.** (a) §9 governs — it is the acceptance gate register and the phases agree with
it in all three cases. Cost: none; §2.1's Verifier column becomes a summary, not authority.
(b) §2.1 governs. Cost: two of CHG-015's three countersignatures disappear, including the
email and revision checks that the gate text actually requires. (c) Ask Tyler per case.

**AIM-00 recommends (a).** §9 is described in §0 as the definition of done, §7 agrees with
it on all three, and it is the only one of the two lists that names a verifier for every
clause the gate contains. The register has been seeded showing both, with the discrepancy
marked, so nothing is silently resolved.

---

## D-005 · An item's verifier is not among its phase's verifiers · **bites at Phase 5**

Verified. Two instances, both A11Y-01:

- **CHG-002** — verifier A11Y-01 in §2.1 and §9. Phase 5 is the only phase carrying it and
  names QA-01 + LEDGER-01. A11Y-01's own charter claims Phase 5.
- **CHG-010** — verifier A11Y-01 in §2.1 and §9. Phase 8 names QA-01 + LEDGER-01 + SEC-01.
  A11Y-01's own charter claims Phase 8.

Related and worth resolving together: A11Y-01's stated callable gate is contrast, hue
independence and keyboard access. CHG-002's gate ends *"30-day total reconciles with the
master ledger"* — a reconciliation, which is LEDGER-01's competence and outside anything
A11Y-01's charter says it may call.

**Options.** (a) Add A11Y-01 to the verifier line of Phases 5 and 8, and split CHG-002's
gate so A11Y-01 calls the visual clauses and LEDGER-01 calls the reconciliation clause.
Cost: one more countersignature at two phases. (b) Move CHG-002's and CHG-010's verifier to
match the phase. Cost: contrast and keyboard clauses get called by agents whose charters do
not cover them — the exact failure §4.2 exists to prevent. (c) Leave it and let both call.
Cost: nobody is accountable, which §6's one-owner logic exists to prevent.

**AIM-00 recommends (a).**

---

## D-006 · CHG-010's owner is DS-01 in §2.1 and ADMIN-01 at Phase 8 · **bites at Phase 8**

Verified. §2.1 gives CHG-010 to DS-01. Phase 8 is the only phase carrying it, is owned by
ADMIN-01, and lists CHG-010 in line. DS-01's charter also says *"Must not: redesign
screens. DS-01 supplies the system; UX-01 and ADMIN-01 apply it."*

**Options.** (a) ADMIN-01 owns the screen application at Phase 8; DS-01 owns the row-weight
token it consumes. Cost: none — it is what both charters already describe. (b) DS-01 owns
it and Phase 8 gains a second owner. Cost: DS-01 redesigning a screen, against its own
charter.

**AIM-00 recommends (a),** and notes it is a clarification rather than a scope change: no
work moves in or out, only the name on it.

---

## D-007 · SK-51 has two owners in §6 and none in any charter · **bites at Phase 18**

Verified. §6 Family H lists SK-51's owner as `UX-01 + ADMIN-01`. §6's own first rule is
*"Every skill has exactly one owning agent"*; §0 states it as *"No shared ownership."*
Worse: five agents list SK-51 under **Skills executed** — UX-01, ADMIN-01, DOC-01,
CLIENT-BH-01 and GENOME-01 — and **not one lists it as owned.** SK-51 has two owners in the
catalogue and zero in the fleet.

SK-51 is the largest skill in the catalogue (§6.1 calls CHG-015 *"the largest gap"*), so
this is not a labelling nicety: nobody is accountable for the standard of the item that
carries threads, promotion, revision linkage, tenancy surface and notification.

**Options.** (a) UX-01 owns SK-51; ADMIN-01 executes the admin half. Cost: none.
(b) ADMIN-01 owns it. Cost: promotion is admin-only, so this is defensible — but the thread
surface is client-facing and UX-01 owns every client-facing surface. (c) Split into two
numbered skills. Cost: a new SK number, which is a hard stop for Tyler (§12.1, §0.8).

**AIM-00 recommends (a).** Promotion is one act on a client-facing surface, and §12.1's
route exists if it later needs splitting.

---

## D-008 · SK-53 is claimed as owned by both VIZ-01 and QA-01 · **bites at Phase 5**

Verified. VIZ-01's charter: `Skills owned: SK-15, SK-16, SK-17, SK-18, SK-19, SK-20,
SK-53.` QA-01's charter: `Skills owned: SK-43, SK-44, SK-53, SK-56.` §6 Family C names
QA-01. VIZ-01's own charter body then says *"That battery is SK-53 and QA-01 runs it, not
VIZ-01"* — so VIZ-01's ownership line contradicts VIZ-01's own prose.

This is not cosmetic. Phase 5's owner is VIZ-01 and its exit gate is *"the layer survives
the SK-53 hostile battery."* If VIZ-01 owns SK-53, VIZ-01 grades its own battery — the
precise thing §4.2 forbids.

**Options.** (a) QA-01 owns SK-53; strike it from VIZ-01's owned list. Cost: none — §6,
§6.1, QA-01's charter and VIZ-01's own prose all already say so. (b) VIZ-01 owns it. Cost:
a §4.2 violation at a P0 gate.

**AIM-00 recommends (a).** This one is a typographical survivor, not a real disagreement.

---

## D-009 · SK-24's owner is contested three ways · **bites at Phase 13**

Verified. §6 Family D names UX-01 as SK-24's owner. UX-01's charter lists SK-24 under
**Skills executed**, not owned (`Skills owned: SK-12, SK-21, SK-22, SK-23, SK-25`). §4.7
then records QUOTE-01 holding *"SK-24 (intake half)"* and MEMBER-01 holding *"SK-24
(application half)"* — two dormant agents holding named halves of a skill the catalogue
says has one active owner.

**Options.** (a) UX-01 owns SK-24 whole; §4.7's half-claims are read as *what those agents
would inherit if activated*, and are annotated as such. Cost: none. (b) Split the skill.
Cost: two new SK numbers — a hard stop for Tyler. (c) Leave it. Cost: at Phase 13 the form
ergonomics gate has an owner the owner's own charter disclaims.

**AIM-00 recommends (a).**

---

## D-010 · A dormant skill sits inside an in-line item's skill list · **bites now, at §2.4**

Verified, and this is the one with the widest blast radius of the mechanical findings.

§2.1 gives CHG-004 the skills `SK-21–SK-28`. Expanded, that range contains **SK-27**, which
§6 marks DORMANT and whose only owner is the dormant PERF-01. §2.2 puts every dormant skill
out of scope. §2.4 sets one test for whether an agent may act: *"does §2.1 contain an item
it owns or verifies."* §2.1 contains SK-27. Read literally, PERF-01 activates — which §12.2
says can only happen through a §12 filing by Tyler.

Compounding it, two ACTIVE agents list SK-27 in their executed loadouts: VIZ-01 (`SK-08,
SK-09, SK-27, SK-54`) and UX-01 (`SK-24, SK-26, SK-27, SK-28, SK-51, SK-55, SK-56`).

Phase 13, which carries CHG-004's task-flow work, lists its skills individually and
**omits SK-27** — so §7 already reads the way the fence intends.

**Options.** (a) The range is shorthand and Phase 13's explicit list governs: CHG-004's
skills are SK-21–SK-26, SK-28, SK-55, SK-56. Strike SK-27 from VIZ-01's and UX-01's
loadouts. Cost: none; PERF-01 stays dormant. (b) Activate PERF-01 and move latency into
scope. Cost: a scope change, a dormant-role activation, and both are hard stops for Tyler.

**AIM-00 recommends (a)** and will not act on (b) without a §12 filing.

---

## D-011 · A dormant skill is listed as executed by two active standing agents · **bites at Phase 3**

Verified. SK-06 (Claim substantiation, owner COMPL-01) is DORMANT. SITE-01's charter:
`Skills executed: SK-01, SK-06, SK-15, SK-21`. RSCH-01's charter: `Skills executed: SK-06`.
§2.2 places every dormant skill out of scope; §0.3 rule 4 says the dormant skills *"do not
exist for this build."*

**Options.** (a) Strike SK-06 from both loadouts; if a public factual claim is ever added to
the marketing pages, that is the §12 filing that activates COMPL-01, exactly as §4.7 says.
Cost: none. (b) Activate COMPL-01. Cost: a hard stop for Tyler, and no in-line item needs it.

**AIM-00 recommends (a).**

---

## D-012 · Two ACTIVE skills are exercised in no phase · **bites at Phase 1**

Verified. **SK-34** (Pricing strategy publishing, owner ADMIN-01) and **SK-45** (Severity
triage, owner AIM-00) are both marked ACTIVE, appear in no `Skills:` line of any phase in
§7, and appear in no Appendix E row — including the Continuous row. Appendix E's dormant
list does not contain them either, so they are in scope and scheduled nowhere.

SK-45 is the more consequential: severity triage is how §3 gets applied, and §12 step 2
requires AIM-00 to assign a severity to every filed item.

**Options.** (a) Add SK-45 to Appendix E's Continuous row alongside SK-46 — it is
continuous by nature, not a phase's work — and record SK-34 as exercised at Phase 8, where
ADMIN-01 rebuilds the surface that publishes pricing. Cost: none. (b) Mark both dormant.
Cost: SK-34 would remove the admin-preview-equals-member-view check with nothing replacing
it, and SK-45 would leave §3 with no procedure.

**AIM-00 recommends (a).**

---

## D-013 · Phase 1's skills line omits SK-42 · **bites at Phase 1, now**

Verified. §7 Phase 1 reads `Skills: SK-46, SK-43`. Its own Work line says *"pre-written
gates (SK-42)"* and its exit gate says *"every in-line item has a gate written before any
work starts."* Appendix E lists Phase 1 as `SK-42, SK-46, SK-43`.

SK-42 is **NON-WAIVABLE** under §1.2. The phase that exercises it does not list it.

**Options.** (a) Appendix E governs; Phase 1's skills are SK-42, SK-46, SK-43. Cost: none.
(b) §7 governs. Cost: Phase 1 produces gates without citing the non-waivable skill that
governs how gates are written — and §0.3 rule 2 says a role may use only the skills §6
assigns it.

**AIM-00 recommends (a),** and has proceeded on that reading for the register seeding: the
fifteen gates are copied verbatim from §9 rather than authored, which is what SK-42's
"written before work starts" requires and what §1.2 protects.

---

## D-014 · Amendment 1 left four counts stale · **bites at Phase 1, now**

Verified. Amendment 1 changed the scope and the go/no-go list but four statements were not
carried:

| Where | Says | Should say |
|---|---|---|
| Header, `**Change register**` | `16 items captured · 14 in line · 2 scrapped · 7 open decisions` | 17 captured · 15 in line · 2 scrapped · 6 open decisions |
| §7 Phase 1, Work | *"Seed the register with the **14** in-line items"* | 15 — its own exit gate two lines later says 15 |
| Appendix F, Go/no-go row | `15 lines; one addition proposed, not assumed` | 16 lines; the addition accepted by D-002 |
| §8.2 dependency block | `§4.6 decision → Phase 8` | satisfied by D-001; stale, not wrong |

The Phase 1 one is live: the phase about to open contradicts itself between its Work line
and its exit gate. §0.7 step 2 says fifteen, so the packet resolves it — but the protocol
does not.

**Options.** (a) Correct all four; they are transcription lag, not decisions. (b) Leave
them and let the reader reconcile. Cost: the header is the first thing a resuming session
reads (Appendix G's resume prompt), and it would tell that session there are fourteen items.

**AIM-00 recommends (a).** The register has been seeded with fifteen, per §0.7 step 2 and
Phase 1's exit gate.

---

## D-015 · At Phases 19, 20 and 21 nobody performs §4.2's third leg · **bites at Phase 19**

Verified. §4.2 defines three roles at every gate: *"The owner produces the evidence; the
verifier confirms the evidence actually demonstrates the gate; the AI Manager confirms the
verifier did that."*

At Phase 19 the verifier is AIM-00. At Phases 20 and 21 the verifier is AIM-00. In all
three, the agent that would confirm the verifier **is** the verifier. These are the tenancy
proof and both clean passes — the last three gates before launch and the three where an
unchecked countersignature costs most.

**Options.** (a) Tyler performs the third leg at those three gates only, as the one party
above AIM-00. Cost: three reviews, at the end, on the evidence AIM-00 has already assembled
for §11 anyway. (b) Name a different verifier for 19/20/21. Cost: Phase 19's verifier would
have to be an agent that did not build the surfaces (rules out ADMIN-01, UX-01, DOC-01) and
is not the owner SEC-01 — QA-01 is the only candidate, and it is already the executing owner
at 20 and 21. (c) Accept the gap and record it. Cost: the protocol's central rule is
unenforced at exactly the three gates it was written for.

**AIM-00 recommends (a).** It is the only option that does not weaken §4.2, and §11.1
already puts Tyler above the manager at launch.

---

## D-016 · Four gates require a human this session cannot supply · **bites at Phase 11; blocks a P0 and a launch line**

**This is the finding §0.9 describes.** Every path through it either changes a gate or
substitutes for a human, and AIM-00 will do neither on its own.

Verified. Four acceptance signals name a person who is not the build session:

| Gate | Requires | Consequence |
|---|---|---|
| **SK-56 / CHG-004 / Phase 13 exit** | *"A person who has never seen the portal"* completing four tasks unassisted | **CHG-004 is P0.** No launch with an open P0 (§3). |
| **CHG-016 / §11 line 10 / Phase 11 exit / Phase 12b** | *"Spanish copy signed off by a named fluent human"*, and that same human's second sign-off at 12b | A go/no-go line. Named, so unnameable by inference. |
| **CHG-005 / SK-18 / Phase 7 exit** | *"A reader ranks all clients correctly from the bars alone"* | P1. See also D-017. |
| **Phase 12 / CHG-004b** | *"what a purchasing manager at a food-service company would actually recognize"*, countersigned by CLIENT-BH-01 | Gates Phase 12b and everything after. |

The tempting move is to run a cold-context subagent that has never seen the portal and
call it the naive user, and to have a Spanish-capable agent sign the copy. **AIM-00 will
not do that and is not recommending it.** A gate that says "a person" and is passed by a
model is a partial pass reported as a pass, which §1.10 calls the most expensive failure in
the document. Substituting quietly is worse than failing loudly.

**Options.**

**(a) Tyler supplies the humans.** One naive tester for SK-56, one named fluent Spanish
reviewer for CHG-016 and Phase 12b, one reader for the bars test, and Tyler himself or a
Boars Head contact for Phase 12. Cost: real scheduling, in four places, and the Spanish
reviewer is needed twice, at Phase 11 and again at Phase 12b. Nothing else changes.

**(b) Tyler rewrites the four gates before the work, under §1.2** — which permits a wrong
gate to be *"escalated to the AI Manager and rewritten before the work, never after."* We
are before the work, so this is the legal window and it closes when Phase 4 opens. Cost:
the gates get weaker, and CHG-004's gate is the one thing standing between "the portal is
simpler" and "someone who has never seen it can actually use it."

**(c) Split each gate into the machine-checkable part and the human part**, pass the first
now, and carry the second as an explicit §11.1 override line so the risk is visible rather
than forgotten. Cost: launch happens with four gates half-passed, on the record.

**AIM-00 recommends (a) for CHG-016's Spanish sign-off** — it is a go/no-go line, the
protocol names the human deliberately, and a company selling on precision shipping
unreviewed machine Spanish is the exact failure §1.6 and I18N-01's charter exist to
prevent — **and (a) for SK-56/CHG-004**, because it is P0 and because a naive user is the
entire content of that gate.

For **CHG-005's reader** and **Phase 12's purchasing manager**, AIM-00 recommends (a) but
notes both are cheap: the bars test takes one person about a minute, and Phase 12 already
names CLIENT-BH-01 as countersigner, which is an analysis role rather than a person.

**AIM-00 does not recommend (b) or (c) and will not initiate either.** Both are Tyler's
call, and (b) is only legal before the work starts.

---

## D-017 · CHG-005's gate is vacuous after Phase 2 · **bites at Phase 7**

Verified. CHG-005's gate: *"A reader ranks **all clients** correctly from the bars alone
with numbers hidden."* Phase 2 removes every fixture client and Appendix A records the
result: *"first real client; the only client after the Phase 2 purge."* Ranking one client
is not a ranking.

The gate was written against a mature dataset that Phase 2 exists to destroy. Its intent —
share bars legible enough to rank from — is sound and still testable; its stated procedure
is not runnable on the real post-purge data.

**Options.** (a) Run the ranking test against an explicitly labelled local development
dataset — permitted by §1.5, which prohibits fixture data *"outside an explicitly labelled
local development seed"* — and separately verify the real single-client render at Phase 14.
Cost: none, and it is the only option that tests the thing the gate is about. (b) Rewrite
the gate before the work under §1.2. Cost: a weaker gate. (c) Mark it untestable until a
second client exists. Cost: a P1 open at launch, which needs Tyler's explicit deferral by
ID (§3).

**AIM-00 recommends (a).** Note the boundary carefully: the seed is for the *test*, never
for a client-facing surface. §1.5 is non-waivable and this recommendation does not touch it.

---

## D-018 · CHG-001's gate presupposes data Phase 2 may not leave · **bites at Phase 5**

Verified. CHG-001's gate opens *"Seven distinct daily marks. Tallest equals Best Day and
sits below axis max. Marks sum to the headline total."* After Phase 2 the system holds one
client's real history. Whether that history contains seven distinct days with revenue is a
fact about the data, not a property of the chart, and it is unknown until Phase 2 runs.

This is why Phase 2's exit gate requires a **degraded-surface list** and Phase 14 exists.
CHG-001, though, must pass at Phase 5 and again at Phase 8 — both before Phase 14.

**Options.** (a) Read the gate as *"seven distinct daily marks when seven days of data
exist"*, and route the sparse case to Phase 14 and SK-20's defined empty/zero rendering.
Cost: none; SK-20 already owns that rendering and Phase 5 already exercises it. (b) Hold
the gate literally. Cost: a P0 that cannot pass on real data, escalating to RES-01 the
moment Phase 5 opens.

**AIM-00 recommends (a),** and flags that Phase 2's degraded-surface list should be
consulted before Phase 5 opens rather than at Phase 14, since it determines whether CHG-001
is testable at all. That is a sequencing observation, not a proposal to reorder phases.

---

## D-019 · Four gates score against a threshold the document never states · **bites at Phase 4**

Verified. §6 defines a skill as having *"a falsifiable acceptance signal — a check that is
either true or false, with no judgment call in the middle."* Four gates do not meet it:

- **Contrast.** SK-08 and CHG-013 require *"minimums"* / *"contrast minimums"*. No standard
  is named, no ratio given, no distinction between normal text, large text and UI
  components. **Bites at Phase 4**, whose exit gate is the token set, and at Phase 7.
- **CHG-004's step counts.** The gate requires each task *"under a stated step count"*. No
  step count is stated anywhere for submit-quote, find-my-item, view-image or read-my-ledger.
- **CHG-004's sub-items.** Phases 12, 13 and 14 are scoped by letter — 12 takes `b`, 13 takes
  `a, c, d, e, f, h`, 14 takes `g` — but the eight sub-items are never enumerated. Three
  phases are scoped by a list that does not exist in the document.
- **The six Genome sections.** SK-26 and GENOME-01's gate require *"Six client-facing Genome
  sections held"*. Which six is never stated, so "held" cannot be checked.

**Options.** (a) AIM-00 proposes concrete thresholds — a named contrast standard and ratios,
a step count per task, the eight sub-items enumerated from CHG-004's text, the six sections
enumerated from the existing build — Tyler approves them, and they are written into the
register **before Phase 4 opens**. This is §1.2's own procedure and its window is now.
Cost: one round of review. (b) Let each verifier decide at call time. Cost: the gate becomes
whatever the verifier thinks, which is the negotiable gate §1.2 exists to prevent.

**AIM-00 recommends (a)** and will draft the four for signature on request. It has not
drafted them unasked: numbers written into a gate are the gate, and §1.2 says AIM-00 writes
them *before* the work, with Tyler confirming anything that changes a P0 or P1's meaning.

---

## D-020 · "Cycle" is undefined and is the unit of five gates · **bites at Phase 2**

Verified. *Cycle* carries: RES-01's SLA (*"a path proposed within one cycle"*), §13.2's
trigger (*"any P0 or P1 open longer than one cycle"*), §13.6's own gate (*"no proposed path
older than one cycle"*), §11's restore-drill line as accepted by D-002 (*"within the current
cycle"*), and DATAOPS-01's standing gate. The document never says what one is.

D-002 made this load-bearing for a launch gate, so it is no longer academic.

**Options.** (a) A cycle is one phase — the natural unit here, since work is phase-shaped
and every gate is a phase gate. Cost: none. (b) A cycle is a fixed wall-clock period.
Cost: needs a number from Tyler, and phases will not take equal time. (c) A cycle is one
working session. Cost: sessions are not durable and a resuming session cannot tell how many
have passed.

**AIM-00 recommends (a).** It makes RES-01's SLA checkable from the phase board alone,
which is what a resuming session reads first (Appendix G).

---

## D-021 · A research domain has no in-scope decision to cite against · **bites at Phase 20**

Verified. §5.2 requires **20 qualifying sources on "Payment states, ACH and card settlement
behavior"**, owned by DOC-01. §5.1 requires each source be cited *"against the decision it
informs"*, and RSCH-01's gate (SK-01) requires *"every citation names the decision it
informs."* But CHG-007 is scrapped (§2.2), PAY-01 is dormant with SK-32 and SK-33, and no
in-line item turns on payment state. There is no in-scope decision for those 20 sources to
inform, so they cannot satisfy §5.1's own test.

Phase 20 cannot open until §5 is satisfied in full, and §11 line 5 requires the same. So 20
of 250 sources are, as written, both mandatory and unspendable.

**Options.** (a) Drop the domain; the §5 total becomes 230 and the other eight minimums are
unchanged. Cost: a change to a §5 minimum, which is a scope change under §12 and Tyler's to
sign. (b) Keep it and name the in-scope decisions it informs — CHG-014's totals reconcile to
both ledgers, and a receipt is a settlement artifact, so a narrow reading survives. Cost: 20
sources of work for a thin decision surface. (c) Keep the number and let RSCH-01 accept
citations with no named decision. Cost: waives SK-01's gate, which is the one thing keeping
the research gate from being a page count.

**AIM-00 recommends (a).** (c) is not acceptable and is listed only so the choice is
complete.

---

## D-022 · Phase 16's entry names one of two financial domains · **bites at Phase 16**

Verified. Phase 16's entry: *"§5 financial-document domain satisfied."* §5.2 contains two:
*"Financial document standards — receipts, credit notes, numbering, immutability"* (35) and
*"Payment states, ACH and card settlement behavior"* (20). §5.3 uses the same singular
phrase. Phase 16 builds receipts and credit notes, so the first is clearly meant — but with
D-021 unresolved, whether the second must also be satisfied changes when Phase 16 can open.

**Options.** (a) Phase 16 needs the 35-source document-standards domain only; the second is
governed by whatever D-021 decides. Cost: none. (b) Both. Cost: Phase 16 waits on 20 sources
that may not be spendable at all.

**AIM-00 recommends (a),** and notes it resolves itself if D-021 goes to (a).

---

## D-023 · §4.1's diagram and its prose disagree on three roles · **hygiene**

Verified. The §4.1 diagram places CONTENT-01, GENOME-01 and NOTIFY-01 under **VERIFY**. The
prose four lines below places all three in the **Capability tier** — *"cross-cutting
systems"* — and describes the verification tier as *"never build; verify what others
build."* All three do build: CONTENT-01 owns copy, GENOME-01 owns revision meaning,
NOTIFY-01 owns transactional email.

It matters because §4.2 turns on the builder/verifier split, and all three are also named
verifiers of items they partly build — NOTIFY-01 verifies the email half of CHG-015 and
CHG-016 while owning SK-49, the email skill.

**Options.** (a) Prose governs: all three are Capability tier that also verify halves of
items they do not own, and the diagram is corrected. Cost: none. (b) Diagram governs. Cost:
three agents lose the skills they own, and CHG-016 loses its email owner.

**AIM-00 recommends (a),** and flags NOTIFY-01's dual role as the live instance to watch at
Phase 18 — it should not verify an email it wrote.

---

## D-024 · Two numbering defects · **hygiene**

Verified. **§10 runs from its unnumbered rules straight to §10.4** — there is no §10.1,
§10.2 or §10.3 anywhere in the document, and §10.4 is cited by name in §8.4 and §13.4.
**§7 is titled "THE 21 PHASES" and contains 22 executable steps**, because Phase 12b has its
own owner, verifier, entry, exit gate and evidence. Appendix F acknowledges this
(*"21 + Phase 12b"*) and the heading does not.

**Options.** (a) Number §10's five rules as §10.1–§10.3 and retitle §7 to 22 steps. Cost:
none. (b) Leave both. Cost: a resuming session counting phases from the heading is off by
one, and 12b is *"the single most likely step to be skipped"* by §8.3's own admission.

**AIM-00 recommends (a).**

---

## D-025 · Two charter loadouts are malformed · **hygiene**

Verified. **RES-01's charter names no skills at all** — no *Skills owned*, no *Skills
executed* — while Appendix F says v2.0 gives *"every role ... a skill loadout"* and §0.3
rule 2 says a role may use only the skills §6 assigns it. Read literally, RES-01 may use
nothing, which is incompatible with §13.4's authority to *"reproduce, instrument and debug
on any surface."*

**CLIENT-BH-01's `Skills owned` is not a skill** — it reads *"the Appendix A entry for
MMI-C-1001."* That has no SK number, no §6 row and no acceptance signal, and §6 says a
procedure without an acceptance signal *"is not a skill, it is a wish."*

**Options.** (a) Record that RES-01 executes any skill in service of §13.3's five moves but
owns none and calls none — which is exactly §13.4's shape — and that CLIENT-BH-01's Appendix
A custody is a duty, not a skill. Cost: none; no new SK numbers. (b) Open SK numbers for
both. Cost: two new skill numbers, a hard stop for Tyler, for work that already has a home.

**AIM-00 recommends (a).**

---

# PART 3 — REGISTER OF WHAT IS NOT DECIDED HERE

Nothing in Part 2 has been acted on. The register is seeded, the phase board is set, and no
work has begun. §0.9 forbids AIM-00 amending the protocol, and the four hard stops that
appear above — a new skill number (D-007c, D-009b, D-025b), a dormant-role activation
(D-010b, D-011b), a §5 minimum change (D-021a), and any gate rewrite (D-016b, D-017b,
D-019) — are Tyler's alone under §0.8 and §12.

---

# PART 4 — FILED FROM PHASE 1'S INVENTORY

Three more, found by measuring the frozen build rather than reading the protocol. Same
rule: filed, not resolved.

---

## Superseded — the Phase 1 findings behind D-026 and D-027

AIM-00 filed two findings under these numbers at Phase 1: *two in-line items describe
a defect the build does not have*, and *VIZ-01's charter diagnoses a defect that is not
the one present*. Both are answered by Tyler's signed D-026 and D-027 in Part 1, which
carry the same subjects. The findings are not deleted — they are the questions those
decisions answer, and they are quoted inside them.

---

## D-030 · CHG-001 and CHG-005 are one layer defect, not two screen defects · **bites at Phase 4**

Measured in Chromium. Both items have the same cause: a class name in a template that
`app.css` — the only stylesheet either shell loads — does not define.

| Template asks for | app.css defines | Result, measured |
|---|---|---|
| `.chart-bar`, `.chart-svg`, `.chart-grid`, `.chart-axis`, `.chart-wrap` | nothing (its chart rules at 288-300 use `.chart …`) | bars `fill: rgb(0,0,0)`, grid `stroke: none` |
| `.meter` + a bare `<span>` | `.meter-head`, `.meter-track`, `.meter-fill` — **used by no template** | meter `127 × 0` px, span `display: inline` at `0 × 0` |
| `.range-row`, `.range-btn` | nothing | period picker is plain text (D-028) |
| `.meter-green` | nothing | — |

§1.4: *"Where two or more items resolve to a common layer … the layer is the unit of
work. Per-screen patching of a shared defect is a protocol violation."* §8.1 predicts
this exact shape.

**Options.** (a) Treat the renderer/token contract as the layer: DS-01 defines the
classes the templates actually use at Phase 4, VIZ-01 consumes them at Phase 5, and
CHG-001, CHG-005, CHG-010 and D-028 close together. Cost: none — it is the existing
phase order. (b) Fix each screen at its own phase. Cost: a §1.4 violation, explicitly.
(c) Rename the template classes to match `app.css`. Cost: the stylesheet's names describe
a different component (`.meter-head` implies a labelled meter the templates do not
build), so this fits the markup to the leftovers rather than the other way round.

**AIM-00 recommends (a).** Note the ordering already works, so this is a framing decision
rather than a resequencing one — but it changes what Phase 4's exit gate has to cover,
and that gate is pre-written, so it is Tyler's under §1.2.

---

## D-031 · CHG-001's marks do not sum to its headline, and the stylesheet fix will not touch it · **bites at Phase 5**

`analytics.series()` emits `days` calendar buckets starting from the window's start date,
while `analytics.summary()` sums the same window including today. Today's revenue is in
the total and has no bar. The gap is **1,911,346 cents at every one of 7d, 21d, 45d, 90d,
180d and 365d** — identical because it is always the same missing day. The oldest bar is
the mirror: a partial day drawn as a full one.

CHG-001's gate: *"Marks sum to the headline total."* VIZ-01's charter: *"A chart that
disagrees with the ledger is a P0 regardless of how it looks."*

This matters because it is invisible to the work everyone expects to do. The black chart
is what got reported; fixing the stylesheet makes the bars green and leaves the
arithmetic exactly as wrong, and the surface will then look correct while under-reporting
by a day.

**Options.** (a) It is inside CHG-001's existing gate clause, so Phase 5 fixes it and
LEDGER-01's reconciliation is what proves it. Cost: none, no new item. (b) File it as its
own CHG with its own gate, since a rendering defect and an arithmetic defect are
different work with different verifiers. Cost: a new register item — Tyler's under §0.8.
(c) Treat it as a P0 in its own right: CHG-001 is already P0, and this half is a money
surface disagreeing with itself.

**AIM-00 recommends (a),** and flags that CHG-001 cannot be closed on the chart looking
right — the clause that catches this is "marks sum to the headline", and LEDGER-01, not
QA-01, is the verifier who would notice.

---

## D-032 · A defect on an in-line surface that no in-line item covers · **bites at Phase 8**

Measured. `.range-row` and `.range-btn` are also undefined in `app.css`, so the revenue
screen's period control renders as plain text: `background rgba(0,0,0,0)`, `border-width
0px`, `padding 0px`, no visible active state. `1D 7D 21D 45D 90D 180D 365D` is a row of
words that happen to be links.

No in-line item covers it. CHG-009 covers the period *vocabulary*; CHG-013 covers contrast
and colour-only status; CHG-010 covers button weight in tables. A control that does not
look like a control is none of those.

Per §1.9 this is filed and not built.

*Filed by AIM-00 at Phase 1 as D-028. Renumbered to D-032 when Amendment 2 assigned D-028 to a different, signed decision — see the collision note at the head of Part 2.*

**Options.** (a) It rides along with Phase 8, which rebuilds this exact surface on the new
tokens, and closes as part of CHG-001's "correct in both themes" clause without a new ID.
Cost: none, but nothing names it, so nothing checks it. (b) File it as a new CHG under §12
with an ID, a severity and a pre-written gate. Cost: a new register item — Tyler's, under
§0.8. (c) Leave it to Appendix B.

**AIM-00 recommends (b) at P2.** The whole reason this is visible is that Phase 1 measured
rather than read, and the cheapest moment to name it is before Phase 4 sets the tokens it
will consume. But a new CHG item is a hard stop, so it waits for a signature.

---

---

## D-033 · Phase 1's gate clause "no surface is unmapped" has two readings · **bites at Phase 1, now**

Raised by QA-01 when it failed this phase, and it is right that the gate does not
disambiguate.

  Reading A — every surface in the census carries an in-line item.
  Reading B — every surface in the build appears in the census.

Under **A** the gate is unpassable by construction: fifteen items cannot cover 236
distinct surfaces, and 74 rows legitimately carry no item (`/webhooks/stripe`, the
calendar routes, 20 untouched tables). Under **B** it is the completeness check the
phase is obviously for, and it is what §5 assumed without saying so.

SK-42's own standard is *"a gate a third party could run without asking questions."*
This one made a third party ask a question.

**Resolved for now without amending anything:** the census answers both. `surfaces.tsv`
gained an `items` column, so A is computable (167 of 241 rows carry an item, 74 do not)
and B is checkable (the census is generated from `app.url_map`, `PRAGMA table_info` and
the tree). The inventory states both answers rather than choosing.

**Options for the wording itself.** (a) Read it as B and say so in the gate. Cost: none;
it is what the phase is for. (b) Read it as A and rewrite the clause to something
passable — "every surface an in-line item touches is named in the census". Cost: a gate
rewrite, which §1.2 allows only before the work and this phase's work is done. (c) Leave
it ambiguous. Cost: the next verifier asks the same question, and RES-01 cannot answer it
either — §13.4 forbids RES-01 weakening a gate it does not own.

*Filed by AIM-00 at Phase 1 as D-029. Renumbered to D-033 when Amendment 2 assigned D-029 to a different, signed decision.*

**AIM-00 recommends (a).** RES-01 has not touched the clause; it made both readings
answerable and left the wording to Tyler.

---
