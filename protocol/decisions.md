# Decisions, waivers and overrides

Every §4.6-class answer, every waiver and every override, with who signed it, when, and
its expiry. A waiver with no signature, no named owner or no expiry does not exist
(§13.4).

Nothing here is decided. Two answers are outstanding and both are hard stops.

---

## PENDING — D-001 · §4.6 / OPEN-A · admin impersonation controls

**Question:** move OPEN-A into §2.1 as CHG-017 (P1, owner ADMIN-01, verifier SEC-01,
skills SK-37 + SK-52, placed in Phase 8), or decline and leave it in Appendix B.

**Asked of:** Tyler. **Signed:** — **Date:** — **Expiry:** n/a (a scope decision, not a waiver).

**Why it blocks:** Phase 1 cannot open without it (§7 Phase 1 entry; protocol closing
line). Phase 8 cannot open without it (§7 Phase 8 entry; §8.2). §11 line 15 requires it
answered and recorded before launch.

**Where each answer must be applied:**

| Answer | Applies at |
|---|---|
| MOVE IN | §2.1 gains a CHG-017 row · §9's conditional CHG-017 gate becomes live · SK-37 moves DORMANT → ACTIVE in §6 and drops off Appendix E's dormant list · SEC-01 stops "holding SK-37 dormant" (§4.5) · ADMIN-01's "must not implement impersonation controls" charter line is lifted (§4.4) · Phase 8 gains the work and SEC-01 as an additional verifier · Appendix B/OPEN-A is closed as moved |
| DECLINE | SK-37 stays DORMANT · ADMIN-01 flags and stops at the impersonation path (§4.4, §7 Phase 8) · SEC-01 records the exposure as a named accepted-risk line in the Phase 19 attempted-access matrix (§7 Phase 19) · §11 carries it as an explicit override line so the risk is visible (§4.6) · Appendix B/OPEN-A stays open |

**AIM-00 note:** the protocol recommends MOVE IN and states its reasoning at §4.6. It
also states that either answer is workable and that no answer is not. AIM-00 does not
decide this; §1.9 and §12 put scope with Tyler.

---

## PENDING — D-002 · §11.2 · SK-41 restore drill as a go/no-go line

**Question:** accept the proposed 16th go/no-go line — *"A restore drill completed and
timed within the current cycle"* — or decline it.

**Asked of:** Tyler. **Signed:** — **Date:** — **Expiry:** —

**Why it blocks:** it is not listed as a Phase 1 entry condition, but it changes
DATAOPS-01's standing gate from Phase 2 onward, so it is cheaper to answer now than to
re-run Phase 2's verification later.

**Where each answer must be applied:**

| Answer | Applies at |
|---|---|
| ACCEPT | §11 gains the 16th line · SK-41 stays ACTIVE in §6 Family F · §9's cross-cutting line stands · DATAOPS-01's gate keeps its restore-drill clause (§4.5) · Appendix E keeps SK-41 in the Continuous row |
| DECLINE | the line is removed from §11 · SK-41 becomes DORMANT in §6 · **§9's cross-cutting clause "A restore drill completed within the cycle (SK-41, §11.2)" must also be struck** · DATAOPS-01's gate (§4.5) drops the restore-drill clause · Appendix E's Continuous row drops SK-41 · SK-41 joins Appendix E's dormant list, making it eleven dormant skills, not ten |

**AIM-00 note:** §11.2 states it as proposed and explicitly not assumed, but four other
places in the document already read as though it were accepted. A DECLINE has to be
applied to all of them or the document contradicts itself from Phase 2 onward.

---

## PENDING — D-003 · §7 Phase 1 verifier versus §13.4

**Question:** who calls the Phase 1 exit gate?

§7 Phase 1 and Appendix E both name **RES-01** as Phase 1's verifier. §13.4 states that
RES-01 **"may not call a gate at all. Gates are called by the named verifier (§4.2).
RES-01 is neither owner nor verifier of anything."**

The owner of Phase 1 is AIM-00, so §4.2 forbids AIM-00 from calling it. As written the
first gate of the build has no agent permitted to call it.

**Asked of:** Tyler, on AIM-00's recommendation. **Signed:** — **Date:** —

**AIM-00 recommendation:** read §7 as the specific instruction and §13.4's clause as a
general statement written before Phase 1 was assigned — i.e. RES-01 calls Phase 1's
completeness sweep and only that, and §13.4 is amended to say "RES-01 is neither owner
nor verifier of anything **except the Phase 1 completeness sweep**." The alternative —
naming a different verifier — costs nothing either, but Phase 1's gate is a completeness
sweep, which is exactly RES-01's competence, and every other active agent is an owner or
verifier of in-line work that Phase 1 is seeding.

This is a protocol amendment, not a waiver. It does not touch a §1 directive.
