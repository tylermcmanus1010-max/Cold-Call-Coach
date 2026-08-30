# MONTI MAKES IT — EXECUTION PROMPT
### Attach with `monti-build-packet.md` and `website-upgrade-packet.md`. Paste this whole file.

> **Tyler — you edit PART 0 and nothing else.**
> Every line below `AUTHORIZATION` is either a severity, a decision, or a credential.
> Until they are filled the agent sets up, reports, and stops — it does not build.
>
> ### `AUTHORIZATION: HOLD`
>
> `HOLD` → validate the filing, report, stop. `GO` → open the next phase and run the loop.

---

# PART 0 — WHAT ONLY YOU CAN SET

## 0.1 Severities — CHG-018 to CHG-035

Confirm or change each. §12 step 4 and §0.9 make P0 and P1 yours, not the agent's.

```
CHG-018 type weight and legibility        [ P1 ]
CHG-019 portal density                    [ P1 ]
CHG-020 return home                       [ P2 ]
CHG-021 call booking                      [ P1 ]
CHG-022 application fields                [ P1 ]
CHG-023 lawful to make and ship           [ P0 ]   <-- proposed P0
CHG-024 disclaimers and acceptance        [ P0 ]   <-- proposed P0
CHG-025 privacy statement                 [ P1 ]
CHG-026 declined applicant appeal         [ P1 ]
CHG-027 repeat application detection      [ P2 ]
CHG-028 FAQ                               [ P2 ]
CHG-029 assistant                         [ P2 ]
CHG-030 share and refer                   [ P2 ]
CHG-031 member portal contact             [ P1 ]
CHG-032 manufacturer approval console     [ P1 ]
CHG-033 feedback                          [ P2 ]
CHG-034 testimonials                      [ P1 ]
CHG-035 French                            [ P2 ]
```

## 0.2 The three decisions from the filing

```
D-039  testimonials or reviews    [ (a) selected testimonials, labelled | (b) real reviews | DECLINE ]
D-040  what the assistant may say [ (a) navigation + FAQ only | (b) larger scope, refile | DECLINE ]
D-041  declined-applicant record  [ (a) hashed contact + date + reason, 24mo | (b) full record | DECLINE ]
```

## 0.3 Two dormant activations

```
COMPL-01  for CHG-023            [ ACTIVATE | DECLINE ]
MEMBER-01 for CHG-026, CHG-027   [ ACTIVATE | DECLINE ]
```

Declining COMPL-01 does not remove CHG-023 — it removes the only role chartered to own it,
and the item then has no owner. Say which you mean.

## 0.4 The launch decisions — new, and the reason this prompt exists

**D-042 — where it runs.** The engine has a `Dockerfile`, a `Procfile` and a 38-variable
`.env.example`. It has never been deployed anywhere. Name the host and the domain, or say
"decide later" and launch stays a word.

```
host   [ Fly.io | Render | Railway | a VPS | other: ______ | decide later ]
domain [ ____________________ | decide later ]
```

**D-043 — the database, and a contradiction you should see now.**
The engine stores everything in SQLite at `DATABASE_PATH`. On every host above except a
VPS with a mounted volume, container disk is ephemeral: **a redeploy destroys the
database.** You accepted SK-41 as a go/no-go line — "a drill means an actual restore,
actually timed" — and there is nothing to restore from a disk that does not persist. The
two cannot both stand.

```
[ (a) managed Postgres — a real migration, its own filing, the only option that makes
      SK-41 mean anything on a container host ]
[ (b) SQLite on a mounted persistent volume + scheduled offsite backup — smaller, ties
      you to hosts that offer volumes ]
[ (c) SQLite as-is and SK-41 withdrawn — cheapest, and it means accepting that the
      commercial history of every client is one redeploy from gone ]
```

AIM-00 recommends **(b)** to launch and (a) before the second client.

**D-044 — credentials.** No agent can supply these and none should invent them. Nothing
that depends on a missing one gets built against a fake.

```
SMTP host / user / password      [ supplied | not yet ]   blocks: CHG-021, CHG-024, CHG-026, CHG-033
Stripe secret / publishable      [ supplied | not yet ]   blocks: real checkout
Stripe webhook secret            [ supplied | not yet ]   blocks: settlement confirmation
```

---

# PART 1 — WHERE THE EIGHTEEN GO

Most of them are not new phases. §1.4 makes the layer the unit of work, and four of these
items are the same layer an existing phase already opens.

| Item | Rides | Why there |
|---|---|---|
| CHG-018 type weight | **Phase 4** | DS-01 already authors the tokens there; this is one more token rule, not a second pass over the same file |
| CHG-019 portal density | **Phase 13** | UX-01's task-flow rebuild is where screens get simplified; doing it separately means rebuilding twice |
| CHG-020 return home | **Phase 13** | Same rebuild, same shell |
| CHG-035 French | **Phase 11** | The string table Spanish creates is the one French uses. Before Phase 10 there is no table, and adding a language means doing Phase 10 badly twice |

The remaining fourteen need phases that do not exist. Six new ones, numbered from 22 so
nothing renumbers:

| Phase | Name | Owner | Verifier | Items |
|---|---|---|---|---|
| **22** | Lawful to make and ship | COMPL-01 | SEC-01 | CHG-023 |
| **23** | The application, rebuilt | UX-01 + NOTIFY-01 | QA-01 + CONTENT-01 | CHG-021, CHG-022 |
| **24** | Disclaimers, privacy and recorded acceptance | DOC-01 + CONTENT-01 | LEDGER-01 + SEC-01 | CHG-024, CHG-025 |
| **25** | Membership decisions | MEMBER-01 | CONTENT-01 + SEC-01 | CHG-026, CHG-027 |
| **26** | Manufacturer approval console | ADMIN-01 | SEC-01 | CHG-032 |
| **27** | Help, contact and social proof | UX-01 + CONTENT-01 | QA-01 + AIM-00 | CHG-028, CHG-029, CHG-030, CHG-031, CHG-033, CHG-034 |

## 1.1 Where they sit in the sequence, and why

**Phase 22 opens immediately after Phase 2.** It is the only P0 candidate that depends on
nothing — not the tokens, not the charting layer, not the documents. It is an intake gate,
intake exists today, and every day it is not there is a day someone can ask Monti to make
something it may not lawfully make. Putting it at the end because it is new would be
sequencing by filing date rather than by risk.

**Phase 26 opens before Phase 19.** A new role with its own access boundary is a tenancy
surface, and Phase 19 is where tenancy is proved adversarially. Building the console after
the proof means the proof did not cover it.

**Phase 24 follows Phase 16.** Recorded acceptance is an immutable document with a version
hash — the same machinery as the receipt, built by the same agent, verified by the same
one. After Phase 16 it is an afternoon; before it, it is Phase 16 done twice.

**Phase 23 and Phase 25 are a pair and 25 follows 23.** The appeal path replies to a
decline on an application, and Phase 23 changes what an application is.

**Phase 27 is last of the six.** Every item in it is content on surfaces the earlier phases
rebuild. Writing the FAQ against a portal that Phase 13 is about to re-lay-out is writing
it twice.

**Revised sequence:** 1, 2, **22**, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12b, 13, 14, 15, 16,
**24**, 17, 18, **23**, **25**, **26**, 19, **27**, 20, 21.

Twenty-eight steps. It was twenty-two.

---

# PART 2 — THE LOOP

Unchanged from §0.5 of the protocol. Restated because this prompt may be pasted into a
session that has not read it recently.

1. State the phase number, name, owner, verifier and skills.
2. Confirm the entry condition, citing the prior gate's evidence **by file**.
3. Do the work as the owning role, using only that role's skills.
4. Produce the evidence the phase names. Actual command output, actual screenshots, actual
   query results. Never a description of evidence, never "this would show".
5. Hand the gate text and the evidence to the verifier — **only** those two things. Not
   your reasoning, not what you were trying to achieve.
6. On PASS: update the register, report the §0.6 block, open the next phase.
7. On FAIL: RES-01 wakes and runs §13.3's five moves in order, starting with reproduce.
   Report the path in the same cycle.

## 2.1 Four rules this build learned the hard way

They are here because each one already cost a gate:

- **A grep that finds nothing is not evidence of absence.** Two Phase 1 probes reported a
  feature missing because they guessed the class name. Check structurally — enumerate what
  is there — before concluding something is not.
- **Ship the probe, not the conclusion.** Two evidence files were corrected by editing the
  report while the probe that produced them still emitted the old answer. Running the
  documented command overwrote the correction. Every number ships with the script that
  derives it.
- **A charter note that asserts a cause is a finding, not an instruction** (§4.8). Measure
  before believing.
- **An absent defect is not a completed item.** Report it, propose the disposition, let
  Tyler decide (D-026).

---

# PART 3 — WHAT LAUNCH ACTUALLY REQUIRES

This document does not launch anything, and neither does finishing the eighteen items.
**§11 launches.** Sixteen lines, each with attached evidence, and here is where they stand:

| §11 line | State today |
|---|---|
| Zero open P0 | **4 open** — CHG-001, CHG-003, CHG-004, CHG-014. Six if CHG-023 and CHG-024 sign as proposed |
| Zero open P1, or each deferred by ID | **8 open**, becoming 17 — nine of the eighteen are proposed P1 |
| Every P2 closed or deferred with a reason | **2 open**, becoming 9 |
| Two consecutive clean critical-path passes | not started — Phases 20 and 21 |
| §5 research gate: 250 qualifying sources | **0 cited.** Phase 3 covers 55; the other 195 have no phase (D-037) |
| Fixture purge verified | Phase 2 not opened |
| Tenant isolation verified adversarially | Phase 19 not opened |
| Money reconciles four ways | Phase 17 not opened |
| Every issued document retrievable by its party and nobody else | Phase 16 not opened |
| Spanish signed off by a named fluent human | needs a human (D-016) |
| Every phase gate countersigned by a non-owner | Phase 1's gate is **FAIL**, three times |
| Zero register items blocked with no proposed path | holding |
| Appendix A current | holding |
| Appendix B decisions resolved or deferred | **38 filed, 7 signed**; this prompt adds six more |
| §4.6 answered | done, D-001 |
| Restore drill completed and timed | **impossible until D-043** — nothing persists to restore |

Plus four things **no phase covers and no gate tests**, because they are not code:

1. **A host and a domain.** D-042.
2. **A database that survives a redeploy.** D-043, and it is the one that can lose a
   client's history rather than merely delay a launch.
3. **Credentials.** D-044. Email, payments, webhooks.
4. **The legal text itself.** Three gates test that disclaimers exist, are accepted, and
   are recorded immutably. **None tests that the wording is right**, and none can. That is
   counsel's, and no agent in this fleet should draft it.

**The honest summary:** the eighteen items are six phases of work. Launch is those
six plus the twenty-one already sequenced, plus 250 sources, plus two clean traversals,
plus a deploy that has never happened. Anyone who tells you this document launches the
site has not read §11.

---

# PART 4 — FIRST ACTIONS

Regardless of `HOLD` or `GO`:

1. **Read state from disk, not memory** (§0.8): `protocol/phase-board.md`,
   `protocol/register.md`, `protocol/decisions.md`, and the evidence directory for the
   last phase touched. If they disagree with each other, that is a finding — report it and
   stop.
2. **Validate this filing against the register.** Confirm CHG-018 to CHG-035 do not
   collide with an existing ID, that every item has an owner and a verifier that are
   different roles, and that every gate is present. Report any that are not.
3. **Write D-039 to D-044 into `protocol/decisions.md`** with the answers from PART 0,
   the signer, the date, and no expiry — these are amendments, not waivers. Any left
   unanswered is recorded as PENDING and blocks only its own item.
4. **Apply the signed items to the register** with their gates copied verbatim from the
   filing. Severity as set in 0.1. Status OPEN, no evidence.
5. **Update the phase board** with the revised 28-step sequence.
6. **Report the §0.6 block** for where the build actually stands.
7. Then: if `HOLD`, stop. If `GO`, open the next phase per the board.

## 4.1 Hard stops that still apply

Everything in §0.9, and one more specific to this prompt: **if a credential in D-044 is
missing, the item that needs it does not get built against a stub.** File it as blocked,
say what is missing, and move to the next item. A checkout wired to a fake Stripe key is
not a checkout, and a gate that passes against a fake is worse than a gate that fails.

*Written 30 August 2026 against Master Build Protocol v2.0 Amendment 2 and the website
upgrade filing of the same date. Unsigned.*
