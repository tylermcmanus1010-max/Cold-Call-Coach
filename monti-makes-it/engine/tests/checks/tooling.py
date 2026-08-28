"""A31 — tooling disclosure (§11.3.6).

Five assertions, and the fifth is the one that needed real thought.

    four facts, no fifth        the helpful extra line is the failure mode
    the ownership sentence      present on every tooled item, no exceptions
    treatment matches strategy  the line describes what is on screen
    no internal field           what a tool cost us never reaches a client
    the materiality flip        at and above 5%, and not below

The threshold assertion is done at boundary quantities rather than at one
convenient number, because "the callout appears somewhere" and "the callout
appears exactly at the boundary" are different properties and only the second is
what §11.3.4 asks for. The check finds the quantity where the share crosses 5%
and asserts the presentation changes once, there, and in both directions.
"""
from . import Check, Finding


# §11.3.4 fixes the threshold at 5% of landed unit cost. The check states it
# here rather than reading `tooling.MATERIALITY_THRESHOLD`, because a check that
# takes its expected value from the code under test cannot detect that value
# being wrong — move the constant and the boundary moves with it, and everything
# stays self-consistently incorrect. This is the number the protocol specifies;
# if the implementation disagrees with it, that is the finding.
SPECIFIED_THRESHOLD = 0.05


def _boundary_quantity(cost_cents, landed_unit_cents, threshold=SPECIFIED_THRESHOLD):
    """The largest quantity at which tooling is still at or above the threshold.

    share = (cost / qty) / landed, so share >= t  <=>  qty <= cost / (landed * t).
    """
    return int(cost_cents // (landed_unit_cents * threshold))


def run(ctx):
    from monti import tooling

    findings = []
    with ctx.app.app_context():
        tools = ctx.query("SELECT * FROM tools")
        if not tools:
            return [Finding("A31", "no tooled item exists — an unexercised tooling "
                                   "check is not a pass")]

        for tool in tools:
            item = ctx.query("SELECT * FROM catalog_items WHERE id = ?", (tool["item_id"],))
            landed = (item[0]["range_low_cents"] if item and item[0]["range_low_cents"]
                      else 100)

            for strategy in tooling.STRATEGY_TREATMENTS:
                line = tooling.line_for(
                    tool, 100_000, landed, tooling.STRATEGY_TREATMENTS[strategy])

                extra = set(line) - tooling.LINE_FIELDS
                if extra:
                    findings.append(Finding(
                        f"tool {tool['ref']} / {strategy}",
                        f"a fifth fact was added: {sorted(extra)}"))

                if not line["ownership"] or "own it" not in line["ownership"]:
                    findings.append(Finding(
                        f"tool {tool['ref']} / {strategy}",
                        "the ownership sentence is missing from the tooling line"))

                if not line["treatment"]:
                    findings.append(Finding(
                        f"tool {tool['ref']} / {strategy}", "no treatment stated"))

                # The treatment must describe the strategy actually displayed.
                expected = {
                    "amortized": "Spread across",
                    "upfront": "Charged upfront",
                    "upfront_with_sample": "sample run",
                }[tooling.STRATEGY_TREATMENTS[strategy]]
                if not line["reused"] and expected not in line["treatment"]:
                    findings.append(Finding(
                        f"tool {tool['ref']} / {strategy}",
                        f"treatment {line['treatment']!r} does not describe {strategy}"))

                for internal in tooling.INTERNAL_FIELDS:
                    if internal in line:
                        findings.append(Finding(
                            f"tool {tool['ref']} / {strategy}",
                            f"internal field {internal!r} in a client-facing line"))

            # --- the materiality flip, at the boundary ----------------------
            if tool["status"] in ("PAID", "IN_USE") and tool["paid_at"]:
                continue                       # a reused tool has no cost to promote
            cost = tool["client_cost_cents"]
            boundary = _boundary_quantity(cost, landed)

            if tooling.MATERIALITY_THRESHOLD != SPECIFIED_THRESHOLD:
                findings.append(Finding(
                    "tooling.MATERIALITY_THRESHOLD",
                    f"is {tooling.MATERIALITY_THRESHOLD}, but §11.3.4 specifies "
                    f"{SPECIFIED_THRESHOLD}"))

            at = tooling.line_for(tool, boundary, landed, "amortized")
            above = tooling.line_for(tool, boundary + 1, landed, "amortized")
            below = tooling.line_for(tool, max(1, boundary - 1), landed, "amortized")

            # At the boundary quantity the share is still at or above 5%, so the
            # callout is present; one unit more dilutes it below and it must go.
            if not at["material"] or not at["callout"]:
                findings.append(Finding(
                    f"tool {tool['ref']}",
                    f"at {boundary:,} units the share is {at['share_of_unit_cost']:.4f} "
                    f"but no callout fired"))
            if above["material"]:
                findings.append(Finding(
                    f"tool {tool['ref']}",
                    f"at {boundary + 1:,} units the share is "
                    f"{above['share_of_unit_cost']:.4f} — below the threshold — "
                    f"but the callout still fired"))
            if not below["material"]:
                findings.append(Finding(
                    f"tool {tool['ref']}",
                    f"at {boundary - 1:,} units the callout did not fire"))

            # §11.3.4 — the second sentence is mandatory. A callout that states
            # the percentage without stating that it does not recur teaches the
            # client to read a one-time charge as the real price.
            if at["callout"] and "no tooling cost at all" not in at["callout"]:
                findings.append(Finding(
                    f"tool {tool['ref']}",
                    "the materiality callout is missing its mandatory second sentence"))
    return findings


def prove(ctx):
    """Three defects, one per §11.3.6's proof requirement, each reverted."""
    from monti import tooling

    caught = []
    original_line_for = tooling.line_for
    original_fields = tooling.LINE_FIELDS
    original_sentence = tooling.OWNERSHIP_SENTENCE

    # 1. a fifth fact
    def with_fifth(tool, quantity, landed, treatment="amortized"):
        line = original_line_for(tool, quantity, landed, treatment)
        line["expected_lifespan"] = "about 400,000 impressions"
        return line

    tooling.line_for = with_fifth
    try:
        findings = run(ctx)
        hit = [f for f in findings if "fifth fact" in f.detail]
        caught.append(("a fifth fact added to the line", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        tooling.line_for = original_line_for

    # 2. the ownership sentence stripped
    def without_ownership(tool, quantity, landed, treatment="amortized"):
        line = original_line_for(tool, quantity, landed, treatment)
        line["ownership"] = ""
        return line

    tooling.line_for = without_ownership
    try:
        findings = run(ctx)
        hit = [f for f in findings if "ownership sentence" in f.detail]
        caught.append(("the ownership sentence stripped", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        tooling.line_for = original_line_for
        tooling.LINE_FIELDS = original_fields
        tooling.OWNERSHIP_SENTENCE = original_sentence

    # 3. the threshold moved, so the flip no longer happens at 5%
    tooling.MATERIALITY_THRESHOLD = 0.20
    try:
        findings = run(ctx)
        hit = [f for f in findings if "callout" in f.detail]
        caught.append(("the materiality threshold moved off 5%", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        tooling.MATERIALITY_THRESHOLD = 0.05

    missed = [label for label, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{l} -> {n}" for l, _, n in caught)


CHECKS = [Check("A31", "Tooling disclosure: four facts, ownership, treatment, threshold",
                run, prove)]
