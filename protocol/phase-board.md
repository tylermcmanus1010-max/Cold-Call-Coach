# Phase board

**Protocol:** Monti Makes It — Master Build Protocol v2.0, **Amendment 1**, 29 Aug 2026
**Authorization:** `GO`

---

## Current phase

```
PHASE 1 — Freeze and inventory
  gate:      FAIL x2, re-submitted
  owner:     AIM-00            verifier: QA-01 (inventory traversal, D-003)
  skills:    SK-46, SK-43  (+ SK-42 — see D-013)
  entry:     MET — Tyler said go; §4.6 answered by D-001; §0.2 recorded
  frozen at: f0b0e58bf0660a2d3963b3feacbe615b00a948ec
```

**Gate history.** QA-01 has called this gate twice and failed it twice, both times on
clauses 1 and 3 — the completeness of the census and the mapping inside it. Clauses 2 and
4 passed both times. RES-01 woke on each FAIL and ran §13.3 in order; move 1 killed
nothing either time, so both were move 2.

| Run | Verdict | What failed | What RES-01 did |
|---|---|---|---|
| 1 | FAIL | Census omitted Python modules, CLI commands and the prototype while items were mapped onto module paths. `surfaces.tsv` had no item column, so neither reading of "no surface is unmapped" was answerable. 14 factual errors. | Regenerated the census with an `items` column; corrected all 14 in place, marked as corrections. |
| 2 | FAIL | `flask init-db`, `app.py`, `schema.sql` and two of three prototype files still missing. The item column was a substring match over paths — CHG-011 on all 81 templates including 46 with no currency, CHG-005 and CHG-014 missing their real surfaces. Most evidence shipped no probe. **And `.meter` has no rule in `app.css` — the share bars render nothing, which the inventory had attributed to one-client data.** | Census now reads CLI from `app.cli.commands` and derives the item mapping from file content. Every probe ships and reproduces. D-030 filed. |

**res:** §13.3 moves 1–2 both times; moves 3–5 not reached. Nothing is blocked with no
proposed path (§13.6).

---

## Register

15 items, all OPEN, no evidence attached to any. Phase 1 produces the map, not the fixes.

---

## Open decisions

31 filed in `decisions.md`. D-001/002/003 answered by Tyler; D-004 to D-031 open. The
ones that bite before Phase 4 opens:

| ID | One line |
|---|---|
| **D-016** | Four gates name a human this session is not — one of them blocks a P0, one is a launch line |
| **D-019** | Four gates score against thresholds the document never states |
| **D-030** | CHG-001 and CHG-005 are one layer defect, not two screen defects — §1.4 makes the layer the unit of work |
| **D-031** | CHG-001's marks do not sum to its headline at any period; the stylesheet fix will not touch it |
| **D-029** | "No surface is unmapped" has two readings; under one the gate is unpassable |
| **D-013** | Phase 1's skills line omits SK-42, which its own exit gate requires |
| **D-014** | Amendment 1 left four counts stale, one inside Phase 1 |
| D-026 | CHG-002 and CHG-012 describe defects this build does not have |
| D-027 | VIZ-01's charter diagnoses a defect that is not the one present |
| D-028 | The period picker is unstyled; no in-line item covers it |

---

## Next

Nothing opens until QA-01 passes Phase 1. Phase 2 (fixture purge, DATA-01 / DATAOPS-01)
is what follows it.

---

## Standing agents

SITE-01, RSCH-01 and CLIENT-BH-01 run continuously and block nothing (§8.4). None has
filed anything yet. RES-01 has woken twice, on the two FAILs, and is idle between them.
