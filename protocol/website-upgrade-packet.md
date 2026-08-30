# MONTI MAKES IT — WEBSITE UPGRADE FILING

### Attach this alongside `monti-build-packet.md`. It is a §12 filing, not a work order.

> **Tyler — the only lines you edit are the severities and the three decisions.**
> Nothing here is in scope until you sign it. §0.9 makes a new CHG item, a severity, and
> a dormant-role activation three separate hard stops, and this packet trips all three.
>
> ### `FILING STATUS: UNSIGNED`
>
> Change to `SIGNED` when the severities below are confirmed and D-039, D-040 and D-041
> are answered. Until then the agent files and stops.

---

# PART 0 — WHAT THIS IS

**You are AIM-00.** The Master Build Protocol v2.0 Amendment 2 governs; this document adds
to its register and changes nothing else. Read it after the protocol, not instead of it.

Eighteen items, drawn from Tyler's website review of 30 Aug 2026. They are written the way
§12 requires: **the surface, the observed problem in plain words, and why it matters**,
plus the owner, the verifier that is not the owner, the skills, a proposed severity, and
**an acceptance gate written before any work starts** (§1.2, SK-42).

## 0.1 What this filing does not do

- **It does not put anything in scope.** §2.1 is unchanged until Tyler signs.
- **It does not assign severity.** Every level below is *proposed*. §12 step 4 and §0.9
  make P0 and P1 Tyler's.
- **It does not activate a dormant role.** Four items need COMPL-01 or MEMBER-01, which
  §4.7 and §12.2 say activate only on a §12 filing by Tyler. That filing is this document;
  the activation is his signature.
- **It does not write legal text.** Three items carry disclaimers. The gates below test
  that a surface exists, that acceptance is recorded, and that the record is immutable —
  never that the wording is correct. Wording is counsel's, and no gate here pretends
  otherwise.
- **It does not touch the prototype.** D-028: the Flask repo is the build of record and
  the prototype is design intent. Every surface named below is a repo surface.

## 0.2 Three things that cannot be built as described

These are not objections to the work. They are places where the literal instruction and
the protocol's own rules collide, and §0.10 says that is the finding rather than something
to route around.

**D-039 — "Review section (obviously we will control this)."**
A section presented as customer reviews, whose contents are chosen by the seller, is not a
review section. It is advertising wearing a review section's clothes, and a reader cannot
tell. §1.5 forbids fabricated data on a client-facing surface and §11.2 puts that beyond
override. There are two buildable versions and they are different products:
*(a)* **Selected testimonials, labelled as selected** — real quotes, real attribution,
written permission on file, and a visible line saying Monti chooses which appear. Honest,
and it is what most B2B sites actually run.
*(b)* **Reviews, genuinely** — any verified buyer may post, Monti may remove for abuse or
confidentiality under a stated policy but not for being unflattering, and the removal
count is published.
AIM-00 recommends **(a)** now and (b) later if it ever matters, and will build neither
until it is chosen. What it will not build is (a) labelled as (b).

**D-040 — the assistant, and what it is allowed to say.**
A chatbot that answers "what does this cost" has just quoted a price, and §11.1 requires
every figure a client sees to resolve to a published admin input. An assistant that
paraphrases a lead time has made a commitment nobody at Monti approved. The item below is
therefore scoped to **navigation and published FAQ answers only**, with a hard refusal on
price, lead time, capacity and specification, and an escalation to a person instead.
If you want it to quote, that is a much larger item and it needs its own filing.

**D-041 — repeat-application detection versus data minimisation.**
Detecting someone who reapplies after rejection means keeping a record of the rejected —
name, email, probably more — for as long as the detection is meant to work. SK-40 requires
every stored personal field to map to a named purpose with a defined retention. The item
below proposes: **store a one-way hash of the email plus the decision date and reason
code, nothing else, for 24 months.** That answers "have we seen this person" without
keeping a file on people Monti declined. If you want the full record retained instead,
say so and SK-40's data map changes with it.

---

# PART 1 — THE EIGHTEEN ITEMS

Severity column is **proposed**. Verifier is never the owner (§4.2).

| ID | Item | Sev | Owner | Verifier | Skills |
|---|---|---|---|---|---|
| CHG-018 | Body text is too thin and too light to read comfortably | P1 | DS-01 | A11Y-01 | SK-07, SK-08, SK-10 |
| CHG-019 | The client portal shows everything at once | P1 | UX-01 | QA-01 | SK-26, SK-22, SK-55 |
| CHG-020 | No way home from an inner page | P2 | UX-01 | A11Y-01 | SK-21, SK-23, SK-28 |
| CHG-021 | "When can you take a video call?" is a free-text field | P1 | UX-01 + NOTIFY-01 | QA-01 | SK-24, SK-49 |
| CHG-022 | The application assumes every applicant is a company | P1 | UX-01 | CONTENT-01 | SK-24, SK-55 |
| CHG-023 | Nothing asks whether we may lawfully make or ship it | **P0** | COMPL-01 † | SEC-01 | SK-05, SK-24 |
| CHG-024 | No disclaimers surface, and no record that anyone accepted them | **P0** | DOC-01 | LEDGER-01 | SK-29, SK-30, SK-24 |
| CHG-025 | No statement of what we hold and what we never sell | P1 | CONTENT-01 | SEC-01 | SK-40, SK-55 |
| CHG-026 | A declined applicant has no route to reply | P1 | MEMBER-01 † | CONTENT-01 | SK-24, SK-49 |
| CHG-027 | The same declined applicant can reapply indefinitely | P2 | MEMBER-01 † | SEC-01 | SK-40 |
| CHG-028 | No FAQ | P2 | CONTENT-01 | UX-01 | SK-55, SK-21 |
| CHG-029 | No help at the moment someone is stuck | P2 | UX-01 | CONTENT-01 | SK-21, SK-55 |
| CHG-030 | No way to pass the site to someone else | P2 | UX-01 | QA-01 | SK-21 |
| CHG-031 | The member portal has no contact route | P1 | UX-01 | CONTENT-01 | SK-21, SK-55 |
| CHG-032 | Paul approves specifications by telephone | P1 | ADMIN-01 | SEC-01 | SK-34, SK-36, SK-51 |
| CHG-033 | No route for a member to tell us something is wrong | P2 | UX-01 | CONTENT-01 | SK-24, SK-49 |
| CHG-034 | No testimonials, and no honest frame for them | P1 | CONTENT-01 | AIM-00 | SK-55 | 
| CHG-035 | French, and deciding what the language set is | P2 | I18N-01 | CONTENT-01 | SK-48, SK-22 |

† needs a dormant role activated. **CHG-023 activates COMPL-01; CHG-026 and CHG-027
activate MEMBER-01.** Both are §0.9 hard stops and neither happens without your signature.

---

# PART 2 — ACCEPTANCE GATES

Written before the work, as §1.2 requires. Each is meant to be runnable by a third party
who was not present. Where a gate cannot be machine-checked, it says so and names who
signs instead — the same problem D-016 raised about the existing register, handled the
same way rather than papered over.

---

### CHG-018 · Body text is too thin and too light
*Observed:* "A lot of the text on the site looks thin and very light. Not visually
appealing."
*Surface:* `monti/static/css/app.css` — the type tokens; every screen consumes them.
*Why it matters:* This is the layer, not the screens (§1.4). One token set is wrong and
sixty templates inherit it.

> **Gate** *(verifier: A11Y-01)* — No body text renders below 400 weight or below a 4.5:1
> contrast ratio against its own background, in both themes, measured from computed style
> rather than from the stylesheet. Secondary and "dim" text meets 4.5:1, not 3:1 — it is
> used for figures and notes, not decoration. Every size resolves to a scale token
> (SK-10). Evidence: a computed-style sweep over every route in the Phase 1 census,
> reporting weight and measured contrast per text role, with zero failures.

**Note for whoever builds it:** the current `--muted` is used for real content, including
the "how this is counted" notes that CHG-004 requires beside every number. Fixing this by
darkening one token is likely to be most of the work.

---

### CHG-019 · The client portal shows everything at once
*Observed:* "Overload of info. Keep it cut and dry… a few sections with important info…
maybe just run it in the background or have drop down or expand tabs."
*Surface:* the 33 `/portal/*` routes and 20 templates in `monti/templates/portal/`.
*Why it matters:* CHG-004 already mandates simplification; this names the mechanism.

> **Gate** *(verifier: QA-01)* — Every portal surface presents at most **five** primary
> regions above the fold at 1440px and at most **three** at 390px. Everything else is
> reachable, not removed: each hidden region sits behind a labelled disclosure that states
> what is inside it before it is opened. No disclosure hides a figure that another visible
> figure is derived from. Evidence: per-route region counts at both widths, and a list of
> every disclosure with its label and contents.

---

### CHG-020 · No way home from an inner page
*Observed:* "Pages are missing a home button… I think a return home button on all the
pages would be good."

> **Gate** *(verifier: A11Y-01)* — Every route in the Phase 1 census that renders a shell
> carries a visible control returning to that surface's home — the public site's home for
> public pages, the portal dashboard for member pages, the admin dashboard for admin
> pages — reachable by keyboard with a visible focus state, and named in words rather than
> by a glyph alone. Evidence: the route census with a pass/fail column, taken from rendered
> output.

---

### CHG-021 · The call booking is a free-text field
*Observed:* "Needs to be converted into a clickable calendar with date/time and timezone…
export to a representative's calendar… a dropdown with options — regular phone call, zoom,
etc… an optional box for their phone #."
*Surface:* `GET|POST /apply`, `monti/templates/public/apply.html`, the `applications` table.
*Why it matters:* free text means someone reconciles it by hand, and "Tuesday afternoon"
in an unstated timezone is a missed call.

> **Gate** *(verifier: QA-01)* — An applicant picks from **offered slots only**; free text
> cannot produce a booking. The slot carries an explicit IANA timezone, captured from the
> browser and overridable, and both parties see the time in their own zone with the other's
> shown beside it. Channel is chosen from a defined set (phone, video call, in person) and
> is stored, not inferred. Phone number is optional and validated only if present. The
> confirmation email carries a valid `.ics` attachment that imports into a calendar with
> the correct start, duration, timezone and channel — verified by importing it, not by
> generating it. Double-booking the same slot is refused at the data layer. Evidence: a
> booking made end to end, the stored row, the `.ics` imported into a real calendar client,
> and a second attempt on the same slot refused.

---

### CHG-022 · The application assumes every applicant is a company
*Observed:* "Make some of these fields optional because not everyone has a website or an
email… some of these will be private individuals… some of these people are not going to
fit under the 'what do you sell' category."

> **Gate** *(verifier: CONTENT-01)* — An application submits successfully with only:
> a name, one contact method, and what they want made. Every other field is optional and is
> labelled optional. "What do you sell" is replaced by a question that fits an individual
> buying one thing and a brand buying a range, and the replacement is checked against both
> by CONTENT-01. No field is silently required by a downstream screen: a submission with
> the minimum set renders correctly on every admin surface that reads it. Evidence: a
> minimum-field application submitted, then rendered on the incoming queue, the application
> detail and the CRM record.

---

### CHG-023 · Nothing asks whether we may lawfully make or ship it — **P0 proposed**
*Observed:* "A disclaimer regarding legalities and things that may or may not be
manufactured/shipped based on local laws and regulations… especially important when it
comes to things like cannabis or other recreational products."
*Why it matters, and why P0:* every other item here is about a site being nicer to use.
This one is about Monti manufacturing something it may not lawfully manufacture, or
shipping it somewhere it may not lawfully go. It is the only item in this filing that can
cost more than a customer.

> **Gate** *(verifier: SEC-01)* — Every intake path — the public quote form, the portal
> request, and Make This Box — asks the destination country and whether the item falls in a
> restricted category, from a maintained list, before it can be submitted. A submission in a
> restricted category is accepted but **flagged and held**: it does not reach the pricing
> desk until a named person clears it, and the hold is a recorded event with an actor.
> The category list and the jurisdictional note are data, editable without a deploy, with a
> recorded author and date. Evidence: a restricted submission shown held, the hold event
> with its actor, an unrestricted one shown passing through untouched, and the list shown
> editable.

**This gate deliberately does not test the legal wording.** It tests that the question is
asked, that the answer is recorded, and that a person clears the risky ones. The wording is
counsel's and no agent should write it.

---

### CHG-024 · No disclaimers surface, and no record that anyone accepted them — **P0 proposed**
*Observed:* "Make a disclaimers tab… at checkout make checking acceptance of full
disclaimers being read and accepted."
*Why P0:* an acceptance you cannot evidence is not an acceptance. This is the same class of
requirement as SK-30's immutable receipt, and it is proposed under the same discipline.

> **Gate** *(verifier: LEDGER-01)* — A disclaimers page exists and is reachable from every
> footer. Checkout cannot complete without an explicit, unticked-by-default acceptance.
> Acceptance writes an immutable row carrying **who, when, and the version hash of the exact
> text they accepted** — not a boolean, and not a pointer to whatever the text says today.
> The accepted version is retrievable years later and renders as it did on the day. No code
> path edits or deletes an acceptance row. Changing the disclaimer text creates a new
> version rather than mutating the old one. Evidence: an acceptance recorded, the text
> re-rendered from its hash, the disclaimer edited, and the original acceptance shown still
> resolving to the original text.

---

### CHG-025 · No statement of what we hold and what we never sell
*Observed:* "All info is private and we don't sell info disclaimer."

> **Gate** *(verifier: SEC-01)* — The privacy statement names every category of personal
> data the system actually stores, and SEC-01 confirms it against SK-40's data map rather
> than against the copy — a statement that omits a field the database holds is a false
> statement. Retention is stated for each. Evidence: the data map beside the published
> statement, field for field, with no unmatched rows in either direction.

---

### CHG-026 · A declined applicant has no route to reply
*Observed:* "For those who get rejected when applying, there needs to be some sort of
application where they can argue the bid even if they got rejected."
*Activates MEMBER-01.*

> **Gate** *(verifier: CONTENT-01)* — A declined applicant receives a decline that states a
> reason and carries a single-use link to reply. The reply reaches a named reviewer and
> appears on the original application rather than opening a second one. One reply per
> decline; a second is refused with an explanation rather than silently dropped. Evidence:
> a decline issued, a reply submitted and shown attached to the original, and a second
> attempt refused.

---

### CHG-027 · The same declined applicant can reapply indefinitely
*Observed:* "A system that detects people that keep applying after getting rejected so no
one wastes time repeatedly vetting the same person."
*Activates MEMBER-01. See D-041 — this gate assumes the hashed-record answer.*

> **Gate** *(verifier: SEC-01)* — A new application whose contact matches a decline within
> the retention window is flagged to the reviewer with the prior decision date and reason
> code. It is **flagged, not blocked** — circumstances change and an automatic refusal is a
> door welded shut. What is stored is a one-way hash of the contact, the decision date and
> the reason code; SEC-01 confirms no other field of a declined applicant is retained past
> the window, and that the window is enforced by something that runs, not by intention.
> Evidence: a repeat application flagged, the stored row shown to contain only the three
> fields, and an expired record shown gone.

---

### CHG-028 · No FAQ
> **Gate** *(verifier: UX-01)* — Every question is one a real person asked — from support
> mail, applications or calls — and each answer names its source of truth. No answer states
> a price, a lead time or a capacity figure; those change, and a stale FAQ answer is a
> quoted number nobody published (§11.1). Evidence: the question list with its provenance,
> and a scan showing no figure in any answer.

---

### CHG-029 · No help at the moment someone is stuck
*Observed:* "Could add a live AI chatbot on the site to help anyone with FAQs or site
direction."
*See D-040. This gate is written for the narrow version.*

> **Gate** *(verifier: CONTENT-01)* — The assistant answers only from the published FAQ and
> the site's own navigation. Asked for a price, a lead time, a capacity or a specification,
> it declines and offers a person — verified against a written adversarial set including
> indirect phrasings ("roughly what would 50,000 cost"), not only direct ones. It never
> claims to be human. Every conversation is retrievable by the member it belonged to and by
> nobody else. Evidence: the adversarial set with the response to each, and a tenancy check
> on conversation retrieval.

---

### CHG-030 · No way to pass the site to someone else
> **Gate** *(verifier: QA-01)* — A share control on the public site and in the portal copies
> a working link and offers the platform share sheet where one exists. The link carries no
> member identifier, no session token and no referral code that identifies the sender —
> verified by inspecting what is copied. Evidence: the copied string, and a check that it
> resolves for a signed-out visitor.

---

### CHG-031 · The member portal has no contact route
*Observed:* "Member portal is going to need to have a contact us with email, phone #, etc."

> **Gate** *(verifier: CONTENT-01)* — Every portal surface reaches a contact route within
> one click, carrying email, telephone and hours, with the member's account reference
> pre-filled so they do not have to find it. The addresses shown are the ones that actually
> receive — verified against the mail configuration, not against the template. Evidence: the
> route census with the contact affordance per surface, and the addresses matched to config.

---

### CHG-032 · Paul approves specifications by telephone
*Observed:* "Needs to be some sort of manufacturer login where Paul just has to ok stuff and
they see it on the site and he doesn't have to call a bunch of people."
*Why it matters:* WI-I-03 already requires a named engineer to sign a specification before
it becomes a price. Today that signature is a phone call, which means it is not a record.

> **Gate** *(verifier: SEC-01)* — A manufacturer role exists that can see the queue awaiting
> approval and approve or return items with a reason, and **can do nothing else** — no
> pricing, no client data beyond the specification in front of it, no other customer's
> anything, enforced at the data layer and proven by attempted access (SK-36, SK-52). An
> approval is a recorded event with an actor and a timestamp, and it is what releases the
> item onward; nothing else can. Returning an item notifies the desk. Evidence: the
> attempted-access matrix for the role, an approval shown releasing an item, and a
> specification shown unable to reach a price without one.

---

### CHG-033 · No route for a member to tell us something is wrong
> **Gate** *(verifier: CONTENT-01)* — Feedback can be left from any portal surface, carries
> the surface it was left from, reaches a named owner, and the member is told what happened
> to it. Feedback that gets no response within a stated window escalates rather than
> expiring. Evidence: feedback submitted from three surfaces, each shown with its origin and
> its owner, and an unanswered one shown escalating.

---

### CHG-034 · No testimonials, and no honest frame for them
*See D-039. This gate is written for option (a) and does not work for option (b).*

> **Gate** *(verifier: AIM-00)* — Every published testimonial is from a real, identifiable
> customer, with written permission on file, and is quoted rather than paraphrased. The
> page states plainly that Monti selects which testimonials appear. No testimonial is
> composed, edited for sentiment, or attributed to a client who did not say it. Evidence:
> each quote beside its permission record and its unedited source.

**AIM-00 will refuse this item if it is built as anonymous "reviews".** That is not a
gate-negotiation position; it is §1.5.

---

### CHG-035 · French, and deciding what the language set is
*Observed:* "Spanish, French options… or just the most spoken languages, could just change
the small text parts. I wouldn't mess with any important numbers or try to translate
currency."
*Relationship to CHG-016:* CHG-016 is English + Spanish and is unbuilt — there is no string
externalisation at all, and roughly 1,271 hard-coded literals. **French costs almost
nothing once CHG-016 lands and is very expensive before it.** This item should not open
until Phase 10 closes.

> **Gate** *(verifier: CONTENT-01)* — French is added through the same string table as
> Spanish, with no new mechanism. Currency stays USD in every locale, un-converted and
> un-relabelled. No client-authored content is translated (§1.6, non-waivable). Every
> French string is reviewed by a named fluent human before it ships — the same requirement
> as Spanish, and the same open question as D-016. Evidence: the string table diff, the
> reviewer's sign-off, and a currency check across every locale.

---

# PART 3 — WHAT AIM-00 RECOMMENDS ORDERING

Not a schedule — the protocol's phases decide that. This is the dependency shape.

**Before anything else, because they are layers others inherit (§1.4):**
CHG-018 rides with Phase 4's token work. CHG-019 rides with Phase 13's task-flow rebuild.
Both are cheaper inside an existing phase than as their own.

**The two P0 candidates stand alone and early.** CHG-023 and CHG-024 are the only items
here that carry legal exposure rather than product quality, and neither depends on any
other item in this filing.

**CHG-035 waits for Phase 10.** Adding a second language to a build with no string table is
doing Phase 10 badly, twice.

**CHG-032 is larger than it reads.** A new role with its own access boundary is a tenancy
surface, and Phase 19 verifies tenancy. Filed as one item; it may need splitting once
scoped, which is a §12 filing of its own.

**Everything else is independent** and can be placed wherever it fits.

---

# PART 4 — WHAT TO DO WITH THIS

1. Set the severities. Eighteen proposals; two marked P0 and both are the legal ones.
2. Answer **D-039** (testimonials or reviews), **D-040** (what the assistant may say), and
   **D-041** (what is kept about a declined applicant).
3. Confirm or refuse the two dormant activations: **COMPL-01** for CHG-023, **MEMBER-01**
   for CHG-026 and CHG-027.
4. Change `FILING STATUS` to `SIGNED`.

On `SIGNED`, AIM-00 writes these into `protocol/register.md` with their gates verbatim,
records the decisions in `protocol/decisions.md`, places each item in a phase, and reports
the §0.6 block. Nothing is built before its phase opens.

*Filed 30 August 2026. Unsigned, and therefore out of scope.*
