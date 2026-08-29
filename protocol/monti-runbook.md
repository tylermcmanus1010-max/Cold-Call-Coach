# Monti build — how to run it

## The two things only you own

Everything else the fleet handles. These two never leave your hands:

1. **Authorization.** One line at the top of the packet. `HOLD` = set up and stop.
   `GO` = set up and run the next phase. Nothing else starts a phase.
2. **Decisions.** When the agent hits a scope question, a contradiction, or a P0/P1
   severity call, it stops and files a `D-nnn` with options and a recommendation. You answer.
   It never decides these itself, and it may never amend the protocol on its own.

## Setup — once

1. Open Claude Code in the repo.
2. Upload **`monti-build-packet.md`**. That is the only file. It contains the operating
   instructions, all seven signed decisions, and the full protocol.
3. Paste the execute prompt.

That's it. No other files, no other prompts, no configuration.

## The loop — every time

```
       you set AUTHORIZATION           →  HOLD or GO, top of the packet
                 ↓
       you paste the execute prompt
                 ↓
       it works a phase, gates it, reports the §0.6 block
                 ↓
       ┌─────────┴──────────┐
   gate PASS            gate FAIL  →  RES-01 proposes a path, same cycle
       ↓                     ↓
   you say "next"        you approve the path, or answer the D-nnn
```

Every phase ends with the same seven-line block. Read it in this order:

| Line | What you are checking |
|---|---|
| `gate:` | PASS, FAIL or BLOCKED. Never anything softer. |
| `owner:` / `verifier:` | **These must be different roles.** If they match, the gate is void. |
| `evidence:` | File paths. If it reads like a description instead of a path, push back. |
| `open:` | Item IDs still failing. |
| `res:` | Only populated on a FAIL. If a gate failed and this is empty, that's a violation of §1.11. |
| `next:` | What opens now — which is your cue to authorize or hold. |

## When it asks you something

It will file a `D-nnn` with two or three real options, the cost of each, and a
recommendation. Answer in plain words. You don't need a format — but say **which option**,
and say **signed** so it records you as the signer. Example:

> D-031 — take option 2. Signed, Tyler, 3 Sep.

If you disagree with its recommendation, say why in one line. That reasoning goes into the
protocol and shapes how it handles the next one — that's how D-003 and D-027 improved the
document rather than just resolving a ticket.

## When it drifts

Three symptoms, one fix. Paste the correction prompt from **Appendix G** of the packet if
you see any of these:

- the same role produced the evidence and called the gate
- an item reported complete where the evidence is a plan, a summary, or "this would show"
- work on anything that isn't one of the 14 in-line items

## What good looks like

You have already seen it. Phase 1's report self-corrected two of its own probes into the
record, refused to credit existing code against any item, and did not report a gate result it
did not have. That is the standard. Drift away from it is the thing to watch for, and it
usually shows up first as confidence without a file path.

## Red flags

- A gate called PASS with no verifier named.
- "Mostly passing", "essentially done", "should be fine" — §1.10 exists for exactly this.
- An item closed without you signing it. Closing is scope; it's yours.
- The protocol amended without a `D-nnn` and your signature.
- A test that writes to Boars Head's account. §4.5, after D-029.

## The files

| File | What it is |
|---|---|
| **`monti-build-packet.md`** | **The only thing you upload.** Instructions + protocol + all decisions. |
| `protocol/register.md` | Every item, its gate, its status, its evidence. The source of truth for scope. |
| `protocol/decisions.md` | Every D-nnn, who signed it, when. |
| `protocol/phase-board.md` | Where the build is right now. |
| `protocol/evidence/phase-NN/` | The actual proof for each phase. |

When you want to know where things stand without asking the agent, read `phase-board.md`
and `register.md`. They are written to be read by you, not just by it.
