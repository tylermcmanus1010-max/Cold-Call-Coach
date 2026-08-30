# Phase 0 — what is actually true of the build

*30 August 2026. Four verification agents read the code, not the registers, and
returned a verdict per item with evidence. Commit `448d7ce`.*

The registers were stale in both directions: items marked OPEN that are fixed,
one marked CLOSED that is not, and several marked done whose claim does not
survive reading the code. This is the corrected state. Tyler's issue list merges
into this, not into the old registers.

---

## Fixed, and the evidence holds

| | | |
|---|---|---|
| CHG-001 | Revenue chart black block | Chart rules exist at `app.css:589-598`; a live GET emits 7 `chart-bar` marks |
| CHG-005 | Share bars illegible | `.meter` and `.meter > span` defined at `app.css:603-607`; 7 rendered on `/admin/revenue` |
| CHG-018, 020, 024, 025, 028, 029, 030, 031, 033, 034 | Type weight, Home, disclaimers + acceptance, privacy, FAQ, question box, share, portal contact, feedback, reviews | Shipped this session, each with a Class A check |
| CHG-021, 022 | Consultation calendar, application rebuild | A40, five proofs |

---

## The claim-vs-reality cluster — the most serious finding

Five places tell a member, an applicant or a developer that a control exists.
**None of the five exist.** This is worse than a missing feature: a missing
feature is visible, and a false promise is not.

| Where | What it says | What is there |
|---|---|---|
| `public.py:227-230` (FAQ) | "Requests in restricted categories are held for review by a person before pricing" | No restricted question on any intake path; no column that could hold a request |
| `disclaimers.py:163-176` | "A request in a restricted category is held for review by a named person before it reaches pricing" | Same. Published prose, not a control |
| `requests.html:101`, `public.py:206`, `email/order_approved.html:5` | "A named manufacturing engineer signs the final specification" | No manufacturer role, no manufacturer surface. `item_revisions.signed_by` is free text with no write path |
| `public.py:187-191` (FAQ) | "You can reply to the decision on the same application" | No appeal route anywhere |
| `public.py:188-190` (FAQ) | "A reviewer will see that we have spoken before" | No by-email prior-application lookup |

`auth.py` carried a sixth — "read-through only, every write records the admin as
the actor". Neither half was true. **Corrected in place this session**, stated as
false rather than deleted, because a comment asserting a control is how the
control stops being built.

---

## Open, with the diagnosis now precise

**CHG-023 · P0 · No restricted-goods gate.** Verified absent on all three intake
paths and in the schema. The disclaimer text is not a control. Highest-priority
open item.

**CHG-017 · Impersonation has no controls.** Only the admin-side banner exists.
Both routes are GET, no CSRF possible, no reason captured, no confirmation.
`security_log` has **zero writers** — the table is dead weight, and its
`READ_ONLY|WRITE` mode column describes a mode that does not exist. The member is
never told their portal was opened: `viewing_as` is read from the *admin's*
session.

**CHG-014 · No PDF receipt, no credit note.** Zero hits for credit note across
`.py`, `.sql`, `.html`. No PDF library in `requirements.txt`. No `@media print`,
no `window.print`. Admin retrieval of any member's receipt is unscoped and
unlogged.

**CHG-032 · No manufacturer console.** Two roles exist, `ADMIN|CLIENT`. The
"manufacturer review" in the code is a 24-hour hold on a paid order, closed by an
admin — an admin action wearing a manufacturer label.

**CHG-003 · Fixture sweep covers 7 of 52 tables.** The schema grew from 45 to 52;
the sweep did not. Concrete leak: `calendar_events` is seeded, is not in
`FIXTURE_TABLES`, is not in `ORPHAN_CHECKS`, and its FK is `ON DELETE SET NULL`
— so seeded events survive a purge with a nulled `customer_id` and the purge
still reports clean. The launch guard still checks `customers` alone.
`ORPHAN_CHECKS` detects; it never deletes.

**CHG-001(b) · The revenue arithmetic gap is live.** `series()` emits buckets
from the window start and never emits today; `_totals()` includes today. Measured
across every window: **$26,545.93 missing from the marks**, identical at 7d, 21d
and 90d. The chart renders correctly and adds up to the wrong number.

**CHG-016 · Spanish is ~25%, not done.** 278 entries against 1,113 template
literals. Measured per page: `/quote` 26 translated / 60 not; `/faq` 18 / 44;
`/membership` 21 / 42. On every public page but `/contact`, more distinct phrases
are English than Spanish. The gap is honest — untranslated text renders
byte-identically and `coverage()` reports it — but a Spanish-selecting member
sees a majority-English product.

**CHG-019 · Nothing progressively discloses.** Five `<details>` in the whole
repo, two in the portal, neither structural. `products.html` is now **540 lines**
and renders list, price block, images, genome, stepper, quote panel, slider,
freight selector, three strategy cards, levers, comparison table and price curve
in one scroll — the merge moved work *onto* this page without adding any way to
defer it.

**CHG-002, 008, 009, 013, 015, 026, 027, 035** — all NOT DONE, each verified.
CHG-013 is PARTIAL: badges and deltas carry text, but ledger status is
colour-only (SETTLED has no text marker) and calendar event kinds are conveyed
by border colour alone, with MEETING and INTERVIEW sharing a colour.

---

## Reopened

**CHG-012 · Sign out appears twice — the CLOSED record was wrong.** The count was
taken before the demo bar existed. `_shell.html:16` includes `_demobar.html`
unconditionally, and that carried its own sign-out, so any demo session rendered
two on every page. **Fixed this session** — the bar no longer carries one.

Also fixed: `_shell.html:20` had `\'s` in template text. Jinja has no backslash
escaping there, so the admin view-as bar read *"you are looking at Boars Head\'s
portal"*.

---

## Decisions still unsigned

D-039 testimonials · D-040 assistant · D-041 declined-applicant retention ·
D-042 where it runs · D-043 the database · D-044 credentials.

D-039 and D-040 were **answered by building** — reviews are real-only with
moderation, the assistant retrieves rather than generates. Tyler has not ratified
either. D-043 remains the launch blocker.

---

## What this changes about the issue list

Three things worth knowing before writing it:

1. **Ten items are already fixed.** Listing them spends the fleet on nothing.
2. **The claim-vs-reality cluster is not five features.** It is one decision —
   do we build the control, or stop saying it exists — and the answer might
   differ per row.
3. **CHG-001(b) is invisible to a reviewer.** The chart looks right. Nobody
   would put it on a list from looking at the screen.
