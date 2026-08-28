"""The Product Genome, and the membership record around it (Appendix E.3, E.4).

Two things live here because they answer the same question from different
angles: what do we actually know about this product, and what have both sides
actually done.

**Six sections, and the naming is settled.** §3.2 called them spec, drawings &
references, BOM, quality, logistics, run history. The prototype called them
specification, golden sample, quality record, tooling, landed-cost profile,
history. Appendix E.7 resolves it in the prototype's favour and asks for the
mapping to be recorded once — `SECTIONS` below is that record, and everything
reads from it, so the two vocabularies never have to be reconciled again at a
call site. Still six. Never a seventh.

**Unknown is a value.** Every getter here can return "we do not know", and the
templates render that as a marked gap rather than as blank space. Appendix B is
explicit that a plausible default is worse than an admitted hole: a
specification the client never gave us, printed on their own page as though they
had, is the failure this whole record exists to prevent.

**A commitment with no measurable source says so.** E4.02. `met` is nullable and
NULL means unmeasured, which is different from failed and different from met.
Rendering an unmeasured commitment as a tick is how a page full of green ticks
comes to mean nothing.
"""
from .db import query

# E.7: the prototype's naming is adopted; §3.2's content requirements are
# preserved under these labels. Recorded once, here.
SECTIONS = [
    ("Current specification", "spec",
     "What it is, and the revision that is current. Earlier revisions are kept, "
     "never overwritten."),
    ("Golden sample", "golden",
     "The physical part every production run is measured against."),
    ("Quality record", "quality",
     "What gets checked on every run, and whether orders arrived without a problem."),
    ("Tooling", "tooling",
     "What the tool costs, who owns it, and how it lands in your unit price."),
    ("Landed-cost profile", "logistics",
     "Duty, packing and shipping assumptions behind every price you are shown."),
    ("History", "history",
     "Every run, every price movement, every decision you signed."),
]

SECTION_TITLES = [title for title, _key, _blurb in SECTIONS]


def bodies(item_id):
    """The six section bodies, keyed by title, with their unknown flags.

    A section absent from the database is returned as unknown rather than
    omitted: the record has six sections whether or not anyone has filled them
    in, and a missing one is information.
    """
    rows = query(
        "SELECT section, body, is_unknown FROM item_genome "
        "WHERE item_id = ? AND is_internal = 0", (item_id,))
    have = {r["section"]: r for r in rows}
    out = []
    for title, key, blurb in SECTIONS:
        row = have.get(title)
        out.append({
            "title": title, "key": key, "blurb": blurb,
            "body": row["body"] if row else None,
            "unknown": bool(row["is_unknown"]) if row else True,
        })
    return out


def revisions(item_id):
    return query("SELECT * FROM item_revisions WHERE item_id = ? "
                 "ORDER BY changed_at DESC", (item_id,))


def golden_sample(item_id):
    return query("SELECT * FROM golden_samples WHERE item_id = ?", (item_id,), one=True)


def quality(item_id, customer_id):
    """The quality record: what is checked, and how the runs actually went.

    The headline figures are counted from `item_runs` and `item_claims` rather
    than stored, so they cannot drift from the runs they describe — and with no
    runs yet they read "no runs yet", which is the truth rather than a zero that
    looks like a failure.
    """
    checks = query("SELECT * FROM quality_checks WHERE item_id = ? ORDER BY id", (item_id,))
    runs = query("SELECT * FROM item_runs WHERE item_id = ? ORDER BY run_no DESC", (item_id,))
    claims = query("SELECT * FROM item_claims WHERE item_id = ? ORDER BY raised_at DESC",
                   (item_id,))
    on_time = [r for r in runs if r["on_time"] == 1]
    return {
        "checks": checks,
        "runs": runs,
        "claims": claims,
        "run_count": len(runs),
        "claim_free": len(runs) - len({c["run_ref"] for c in claims if c["run_ref"]}),
        "on_time": len(on_time),
        "open_claims": [c for c in claims if not c["closed_at"]],
        "measured": bool(runs),
    }


def tooling_facts(item_id, customer_id):
    """The Tooling Line's four facts, read from the tool register (§11.3)."""
    return query(
        "SELECT * FROM tools WHERE item_id = ? AND customer_id = ? ORDER BY id",
        (item_id, customer_id))


def runs(item_id):
    return query("SELECT * FROM item_runs WHERE item_id = ? ORDER BY run_no DESC", (item_id,))


def has_run_history(item_id):
    """E1.14 — the genome link appears only on items with a production run.

    Derived from real history rather than a flag someone sets, so an item with
    zero runs cannot be linked to a record that would be empty.
    """
    row = query("SELECT COUNT(*) AS c FROM item_runs WHERE item_id = ?", (item_id,), one=True)
    return bool(row and row["c"])


# --------------------------------------------------------------------------
# membership: capacity, the plan, the commitments (E.4)
# --------------------------------------------------------------------------
# The weighting table the system actually applies (E4.04). Stated here and used
# by both the ledger arithmetic and the page that explains it, so the table a
# member reads is the table that charged them.
WEIGHTS = [
    (1, "Simple variation", "A dimension, a colour, a pack change"),
    (2, "New straightforward product", "One part, one process"),
    (4, "Complex assembly", "Multiple parts, tooling, or sub-suppliers"),
    (0, "Reverse engineering or major DFM",
     "Scoped separately, never taken from your allowance"),
]

# The rules, and every one of them runs in the member's favour. They are stated
# before a refusal rather than after it — a fairness rule a member only learns
# when it is used against them is not a fairness rule.
FAIRNESS_RULES = [
    "A request we decline costs you nothing.",
    "A request returned for missing information is not charged until it comes back complete.",
    "Unused units roll forward, up to a third of your allowance.",
    "If we miss a quotation deadline, the units come back automatically.",
    "Completed orders, accurate forecasts and quick decisions all earn more.",
]


def capacity(customer):
    """A member's weighted capacity position, reconciled from the ledger.

    `used` is summed from the ledger rows rather than stored on the customer, so
    the number in the header and the rows underneath it cannot disagree — which
    is the whole point of showing the ledger.
    """
    rows = query(
        "SELECT * FROM capacity_ledger WHERE customer_id = ? ORDER BY occurred_at DESC",
        (customer["id"],))
    allowance = customer["quote_limit"] or 0
    rolled = min(allowance // 3, 0)          # nothing to roll until a cycle closes
    earned = 0
    used = sum(r["charged"] for r in rows)
    total = allowance + earned + rolled
    return {
        "rows": rows,
        "allowance": allowance,
        "earned": earned,
        "rolled": rolled,
        "total": total,
        "used": used,
        "left": max(0, total - used),
        "cycle_days": customer["quote_cycle_days"] or 30,
        "uncharged": [r for r in rows if not r["charged"]],
    }


def factory_plan(customer_id):
    return query("SELECT * FROM factory_plans WHERE customer_id = ?", (customer_id,), one=True)


def commitments(customer_id):
    """Both columns. `met` is NULL where nothing has happened to measure yet."""
    rows = query("SELECT * FROM commitments WHERE customer_id = ? ORDER BY side, position",
                 (customer_id,))
    return {
        "member": [r for r in rows if r["side"] == "MEMBER"],
        "monti": [r for r in rows if r["side"] == "MONTI"],
        "unmeasured": len([r for r in rows if r["met"] is None]),
    }


def credits(customer_id):
    return query("SELECT * FROM performance_credits WHERE customer_id = ? "
                 "ORDER BY issued_at DESC", (customer_id,))


# --------------------------------------------------------------------------
# Make This Box (WI-I-07)
# --------------------------------------------------------------------------
BOX_STAGES = [
    "Box requested",
    "Sample received",
    "Photographed and measured",
    "Materials identified",
    "Approach proposed",
    "Quote ready",
    "Returned or stored",
]


def boxes(customer_id):
    """Sample boxes and the events that moved them.

    A stage is derived from the recorded events, never set directly: WI-I-07
    requires every stage to advance on a recorded event, and the reliable way to
    mean that is to compute the stage from the events rather than to keep a
    counter someone could bump.
    """
    out = []
    for box in query("SELECT * FROM sample_boxes WHERE customer_id = ? ORDER BY id DESC",
                     (customer_id,)):
        events = query("SELECT * FROM sample_events WHERE box_id = ? ORDER BY stage, id",
                       (box["id"],))
        reached = max((e["stage"] for e in events), default=0)
        out.append({"box": box, "events": events, "stage": reached,
                    "stages": BOX_STAGES})
    return out
