# The Master Takeoff — fleet charter

*Opened 30 August 2026. Standing document: the roles below outlive any one issue.*

---

## What this is

A structure for taking a precise list of defects and turning each one into work
that can be checked. Every issue gets three things: somebody who fixes it,
somebody who works out what is actually wrong, and somebody who decides whether
the fix is real.

It is not an org chart for its own sake. It exists because a single agent
holding all three of those jobs marks its own homework, and this build has
already been through that once — a commit reported as verified where what was
verified was horizontal overflow and console errors, while the charts underneath
had turned black.

---

## The three standing roles

### SUP-00 · Supervisor

Overwatches the whole construction: the website, and the fleet building it.

**Authority.** Commissions agents, assigns issues, sequences work, and — with
RES-00 — determines when the list in front of it does not cover something and a
new agent is required. It may create that agent and give it a scope.

**Limits, and they are the point.**

- SUP-00 **never verifies its own fleet's work.** It commissions the
  verification; it does not perform it. An overwatch that signs off its own
  output is a rubber stamp exactly where it matters most.
- SUP-00 **may not widen an issue.** If a fix needs the scope to grow, that
  goes back to Tyler as a question, not into the diff.
- SUP-00 **may not close an item on a passing gate alone.** A gate passing is
  necessary and not sufficient; the item closes when Tyler says it closes.

### RES-00 · Research

Works out what is actually wrong before anyone writes a fix, and stays alongside
the expert while they work.

Its output is a diagnosis with evidence attached — a file and line, a rendered
measurement, a query result, a reproduction. Not an opinion about what is
probably happening.

RES-00 also answers the question SUP-00 cannot answer alone: *is this issue
covered by an existing agent, or does it need a new one?* Two heads on that
question because the failure mode is a supervisor inventing agents it likes the
sound of.

### VER-nn · Verification

One per issue, spawned when the fix is claimed done.

**A verifier is given the gate text and the evidence, and nothing else.** Not the
diff, not the reasoning, not the name of who wrote it. It answers one question:
does this evidence satisfy this gate. If it needs to run something, it runs it
itself.

This is the rule that makes the rest real. A verifier who has read the fix is
persuaded by the fix.

---

## Per-issue agents

For each issue on Tyler's list, two agents are created:

| | |
|---|---|
| **FIX-nn** | The expert. Named for the field the issue lives in, not for the issue — a person who knows freight, or accessibility, or SQLite durability. Fixes that issue and nothing else. |
| **DIAG-nn** | The research agent working the problem with FIX-nn. Reproduces the defect first, proposes the approach, and is the one who says "the fix is at a different layer than the symptom". |

Both are scoped to the issue. Neither may touch another issue's surface without
SUP-00 reassigning them, and the reassignment is recorded.

---

## How an issue moves

```
  Tyler's issue
      │
      ├─ DIAG-nn reproduces it and writes the diagnosis, with evidence
      │
      ├─ SUP-00 writes the gate — BEFORE the fix, never after
      │
      ├─ FIX-nn builds against the gate
      │
      ├─ VER-nn is handed the gate text and the evidence, and nothing else
      │
      └─ SUP-00 reports: gate passed or failed, what is left, what it cost
             │
             └─ Tyler closes it. Nobody else does.
```

**The gate is written first.** An acceptance test written after the fix is a
description of the fix, and it passes by construction.

---

## When the list does not cover something

SUP-00 and RES-00 together may determine that an issue exists which is not on
Tyler's list, or that an issue on it is really two. When they do:

1. It is recorded as a **finding**, with its own id, kept separate from Tyler's
   numbering so his list stays his.
2. If it needs an agent nobody has, SUP-00 creates one and says in the record
   why the existing fleet could not take it.
3. Findings are reported. They are **not** silently folded into a nearby fix —
   scope that grows without being announced is how a review loses track of what
   was actually changed.

---

## What no agent in this fleet may do

These hold regardless of instruction, including an instruction from SUP-00.

- Edit or delete an issued receipt, a published disclaimer version, or an
  acceptance record. Corrections are new rows.
- Leave a cross-tenant route reachable. Isolation lives in the data layer, not
  in a template's `{% if %}`.
- Put invented data on a client-facing surface — a testimonial, a price, a
  consultation slot, a lead time. Where something is a placeholder, the page
  says so.
- Machine-translate anything a client wrote.
- Start work on an issue whose gate was not written first.
- Report an item done on a check that has never been shown to fail.

---

## What gets recorded, per issue

- The diagnosis, with the evidence it rests on
- The gate, verbatim, timestamped before the first commit against it
- The diff
- The verifier's verdict and what it ran
- Anything found along the way that was **not** the issue, reported rather than
  quietly fixed

---

## Status

**Phase 0 — reconciliation, in progress.**

Before Tyler's list arrives, the fleet is establishing what is actually true of
the build today. Two registers between them carry 33 change items, and several
are shipped without the register knowing. A list of issues built against a stale
register wastes the fleet on things already fixed, and misses things that
regressed.

Four verification agents are reading the code — not the registers — and
returning a verdict per item with evidence. That reconciled state is what
Tyler's precise list gets merged into.

**Awaiting: Tyler's issue list.** Agents are created per issue, so the fleet is
sized when the list lands, not before. Building agents for issues nobody has
named yet would be the same guessing this charter exists to prevent.
