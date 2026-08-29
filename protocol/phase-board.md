# Phase board

**Protocol:** Monti Makes It — Master Build Protocol v2.0, **Amendment 2**, 29 Aug 2026
**Authorization:** `HOLD`
**Packet:** `protocol/monti-build-packet.md` (committed alone at `2698336`)

---

## Current phase

```
PHASE 1 — Freeze and inventory
  gate:      being re-called against the amended register
  owner:     AIM-00            verifier: QA-01 (inventory traversal, D-003)
  skills:    SK-46, SK-43  (+ SK-42 — see D-013)
  entry:     MET
  frozen at: f0b0e58bf0660a2d3963b3feacbe615b00a948ec
```

**Every earlier verdict on this gate is void.** QA-01 failed it twice against a register
that has since been amended by D-026 and D-028 — 15 items became 14 in line and 1 closed,
CHG-002's gate was rewritten, and every item is now mapped to a repo surface. §0.8 step 5:
a verdict returned against a register that has since been amended is provisional and does
not carry forward.

| Run | Register it was called against | Verdict | Status |
|---|---|---|---|
| 1 | pre-amendment, 15 OPEN | FAIL — clauses 1 and 3 | void |
| 2 | pre-amendment, 15 OPEN | FAIL — clauses 1 and 3 | void |
| 3 | **Amendment 2**, 14 in line + 1 closed | pending | current |

---

## Register

**14 in line, 1 closed.** CHG-012 is CLOSED by D-026 with the render census attached and
countersigned by QA-01; it stays in the register and any later view rendering sign out
twice reopens that ID rather than opening a new one. Every in-line item carries at least
one Flask-repo surface from the Phase 1 census. **No item cites the prototype** (D-028).

---

## Decisions

33 filed; **seven signed by Tyler** — D-001, D-002, D-003 (Amendment 1) and D-026, D-027,
D-028, D-029 (Amendment 2). D-029 is executed: the residue is reverted and re-proved at
zero.

**ID collision, resolved.** AIM-00 had filed its own findings under D-026 to D-029 at
Phase 1. Two matched Tyler's subjects and merged; two did not. The unsigned agent findings
moved to **D-032** (unstyled period picker) and **D-033** (the ambiguous gate clause);
the signed decisions kept their numbers. Nothing deleted, no number reused.

Open and biting before Phase 4:

| ID | One line |
|---|---|
| **D-016** | Four gates name a human this session is not — one blocks a P0, one is a launch line |
| **D-019** | Four gates score against thresholds the document never states |
| **D-030** | CHG-001 and CHG-005 are one layer defect — §1.4 makes the layer the unit of work |
| **D-031** | CHG-001's marks do not sum to its headline; the stylesheet fix will not touch it |
| **D-033** | "No surface is unmapped" has two readings; under one the gate is unpassable |
| D-013 | Phase 1's skills line omits SK-42, which its own exit gate requires |
| D-014 | Amendment 1 left four counts stale — Amendment 2 fixed the register, not these |
| D-032 | The period picker is unstyled; no in-line item covers it |

---

## Next

Nothing opens on a passing gate. **Phase 2 opens on Tyler's word.**

---

## Standing agents

SITE-01, RSCH-01 and CLIENT-BH-01 run continuously and block nothing (§8.4). None has
filed. RES-01 has woken twice, on the two void FAILs, and is idle.
