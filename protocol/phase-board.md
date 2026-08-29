# Phase board

**Protocol:** Monti Makes It — Master Build Protocol v2.0, **Amendment 1**, 29 Aug 2026
**Authorization:** `HOLD`
**Status:** set up, reported, stopped before Phase 1 (§0.1).

---

## Current phase

```
PHASE 1 — Freeze and inventory
  owner:     AIM-00            verifier: QA-01 (inventory traversal)
  skills:    SK-46, SK-43  (+ SK-42 — see D-013)
  entry:     Tyler says go. §4.6 answered by D-001; §0.2 recorded.
  status:    NOT OPENED — AUTHORIZATION is HOLD
```

Phase 1's verifier is QA-01, not RES-01, by **D-003**. §13.4 stands unamended: RES-01 never
calls a gate, anywhere, with no exceptions. RES-01 is subscribed to Phase 1 as to every
phase — if the gate FAILs, it wakes.

**Entry condition, itemised:**

| Requirement | Source | State |
|---|---|---|
| §4.6 answered | §7 Phase 1 entry | **MET** — D-001, signed 29 Aug 2026 |
| §0.2 recorded | §7 Phase 1 entry | **MET** — recorded in the protocol and in `decisions.md` |
| Tyler says go | §7 Phase 1 entry, §0.1 | **NOT MET** — AUTHORIZATION reads `HOLD` |

Change `AUTHORIZATION: HOLD` to `GO` and Phase 1 opens.

---

## What §0.7 produced

| File | State |
|---|---|
| `protocol/register.md` | **SEEDED** — all 15 in-line items, owners, verifiers, skills, phase, status OPEN, and each acceptance gate copied verbatim from §9 |
| `protocol/decisions.md` | **WRITTEN** — D-001, D-002, D-003 recorded as answered; 22 findings filed as D-004…D-025 |
| `protocol/phase-board.md` | this file |
| `protocol/surface-inventory.md` | **NOT PRODUCED** — Phase 1's output |
| `protocol/citation-register.md` | **NOT OPENED** — Phase 3 opens it |
| `protocol/evidence/phase-NN/` | 22 directories, all empty |

---

## Open

Nothing is failing, because nothing has run. What is open is the 22 findings in
`decisions.md` Part 2. Four of them touch Phase 1 or Phase 2 and are worth answering before
`GO`; the rest can wait for the phase they bite at.

| ID | Bites at | One line |
|---|---|---|
| **D-016** | Phase 11; blocks a P0 and a launch line | Four gates require a human this session cannot supply |
| **D-019** | Phase 4 | Four gates score against thresholds the document never states |
| **D-013** | Phase 1 | Phase 1's skills line omits SK-42, which its own exit gate requires |
| **D-014** | Phase 1 | Amendment 1 left four counts stale, one of them inside Phase 1 |
| D-004 | Phase 1 | §2.1 and §9 name different verifiers for CHG-001, CHG-015, CHG-016 |
| D-012 | Phase 1 | SK-34 and SK-45 are ACTIVE and exercised in no phase |
| D-020 | Phase 2 | "Cycle" is undefined and is the unit of five gates, one now a launch line |
| D-010 | now, at §2.4 | A dormant skill sits inside CHG-004's skill range |
| D-011 | Phase 3 | A dormant skill is listed as executed by two active agents |
| D-005 | Phase 5 | An item's verifier is not among its phase's verifiers |
| D-008 | Phase 5 | SK-53 is owned by both VIZ-01 and QA-01 |
| D-018 | Phase 5 | CHG-001's gate presupposes data Phase 2 may not leave |
| D-017 | Phase 7 | CHG-005's gate is vacuous with one client |
| D-006 | Phase 8 | CHG-010's owner is DS-01 in §2.1 and ADMIN-01 at Phase 8 |
| D-009 | Phase 13 | SK-24's owner is contested three ways |
| D-021 | Phase 20 | A research domain has no in-scope decision to cite against |
| D-022 | Phase 16 | Phase 16's entry names one of two financial domains |
| D-007 | Phase 18 | SK-51 has two owners in §6 and none in any charter |
| D-015 | Phase 19 | At Phases 19, 20 and 21 nobody performs §4.2's third leg |
| D-023 | hygiene | §4.1's diagram and prose disagree on three roles |
| D-024 | hygiene | §10 has no 10.1–10.3; "21 phases" is 22 steps |
| D-025 | hygiene | RES-01 has no loadout; CLIENT-BH-01's owned skill is not a skill |

**res:** nothing has failed, so RES-01 has not woken. It is subscribed and idle (§13.2).

---

## Next

`GO` opens Phase 1: AIM-00 freezes the build and inventories every surface, chart, string,
table and document path; QA-01 traverses the inventory and calls the gate.

The register is already seeded, which is part of Phase 1's work, so Phase 1 opens with that
half done and the inventory outstanding.

---

## Standing agents

SITE-01, RSCH-01 and CLIENT-BH-01 run continuously and block nothing (§8.4). None has
started; the build is not initiated. RES-01 fires on failure only and is never scheduled.
