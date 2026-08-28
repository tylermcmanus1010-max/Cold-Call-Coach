"""The Tooling Line — four facts, always, and never a fifth (§11.3).

Tooling is the most common reason a manufacturing buyer feels ambushed. It is
invisible in the unit price, it lands on the first invoice, and it raises an
ownership question nobody answered. Hiding it protects nothing: the client finds
out on invoice one, at exactly the moment trust matters. Showing the whole cost
structure invites haggling over the wrong number. So the disclosure is fixed at
four facts:

    1. what it is          in words a non-expert reads, never a part number
    2. what it costs       one number — not a build-up, not a range, not "from"
    3. who owns it         the client does, once paid; we hold and maintain it
    4. how it is handled   in *this* strategy, matching what is on screen

The fifth fact is the failure mode this module is built to prevent. A lifespan
estimate, a "typical industry cost", a maintenance schedule — each is helpful in
isolation and each breaks the contract, so `line_for()` returns a fixed-shape
dict and A31 asserts its keys rather than trusting review to catch an addition.

Everything about what a tool cost *us* stays on the row and never reaches a
payload built here.
"""
from .db import query

# §11.3.2, stated the same way every time. Not buried in terms, not conditional.
OWNERSHIP_SENTENCE = (
    "You own it once it is paid for. We hold it, store it and maintain it here. "
    "If you ever want it moved, we release it to you or to another factory at your cost."
)

# The exact keys of a client-facing Tooling Line. A31 compares against this set,
# so adding a field fails a check instead of shipping.
LINE_FIELDS = frozenset({
    "tool_id", "what_it_is", "cost_cents", "ownership", "treatment",
    "per_unit_cents", "share_of_unit_cost", "material", "callout", "reused",
})

# Fields on `tools` that must never appear in anything a client is served.
INTERNAL_FIELDS = ("internal_cost_cents", "internal_notes", "location", "condition")

# §11.3.4 — at or above this share of landed unit cost, the line is promoted to
# a callout above the price.
MATERIALITY_THRESHOLD = 0.05

# §11.3.3 — treatment is one of the things that differentiates the strategies,
# rather than something the client is told afterwards.
STRATEGY_TREATMENTS = {
    "lowest_cost": "amortized",
    "fastest": "upfront",
    "certainty": "upfront_with_sample",
}


def tools_for_item(item_id, customer_id=None):
    sql = "SELECT * FROM tools WHERE item_id = ?"
    args = [item_id]
    if customer_id:
        sql += " AND customer_id = ?"
        args.append(customer_id)
    return query(sql + " ORDER BY id", tuple(args))


def per_unit_price(cents):
    """A per-unit figure at container prices, without lying about precision.

    $840 across 250,000 units is a third of a cent. Rendering that as "$0.00"
    reads as free and rendering it as "$0.0034000" reads as false precision, so
    the fraction keeps four decimals and then loses its trailing zeros.
    """
    dollars = cents / 100
    if dollars >= 0.01:
        return f"${dollars:,.2f}"
    return "$" + f"{dollars:.4f}".rstrip("0").rstrip(".")


def _treatment_text(treatment, cost_cents, quantity):
    """Fact 4. Must describe the strategy actually on screen, so it is derived
    from the treatment passed in rather than written once and reused."""
    if treatment == "amortized":
        per_unit = cost_cents / quantity if quantity else 0
        return (f"Spread across this {quantity:,}-unit run — "
                f"adds {per_unit_price(per_unit)} per unit.")
    if treatment == "upfront":
        return "Charged upfront on your first order; unit price unaffected."
    if treatment == "upfront_with_sample":
        return ("Charged upfront, and proved out on a sample run before the full "
                "quantity releases.")
    raise ValueError(f"unknown tooling treatment: {treatment!r}")


def _callout(share, cost_cents):
    """§11.3.4 — the promotion, and its mandatory second sentence.

    The second sentence is not decoration. A high tooling percentage is
    acceptable precisely because it does not recur, and a client who is not told
    that reads the number as the real price. A31 fails a callout without it.
    """
    return (
        f"At this quantity, tooling is {share * 100:.0f}% of your unit cost. "
        f"It is a one-time charge of ${cost_cents / 100:,.2f} — your next run of "
        f"the same item has no tooling cost at all."
    )


def line_for(tool, quantity, landed_unit_cents, treatment="amortized"):
    """One Tooling Line, as a client sees it.

    `landed_unit_cents` is the landed unit cost the strategy is displaying, and
    the materiality share is computed against it live — so moving the quantity
    slider flips the presentation at the boundary rather than at page load.
    """
    if tool["status"] in ("PAID", "IN_USE") and tool["paid_at"]:
        # §11.3.5 — one of the strongest reasons a second order is cheaper than
        # the first, and it has to be visible rather than absorbed into a
        # quietly lower number.
        return {
            "tool_id": tool["id"],
            "what_it_is": tool["client_description"],
            "cost_cents": 0,
            "ownership": OWNERSHIP_SENTENCE,
            "treatment": "Tooling already made and paid — no tooling cost on this run.",
            "per_unit_cents": 0,
            "share_of_unit_cost": 0.0,
            "material": False,
            "callout": None,
            "reused": True,
        }

    cost = tool["client_cost_cents"]
    per_unit = (cost / quantity) if (quantity and treatment == "amortized") else 0
    share = (per_unit / landed_unit_cents) if landed_unit_cents else 0.0
    material = share >= MATERIALITY_THRESHOLD

    line = {
        "tool_id": tool["id"],
        "what_it_is": tool["client_description"],
        "cost_cents": cost,
        "ownership": OWNERSHIP_SENTENCE,
        "treatment": _treatment_text(treatment, cost, quantity),
        "per_unit_cents": per_unit,
        "share_of_unit_cost": share,
        "material": material,
        "callout": _callout(share, cost) if material else None,
        "reused": False,
    }
    if tool["from_previous_supplier"]:
        # §11.3.5 — a tool the client already owns is never presented as new
        # tooling, and what arrived is stated.
        line["what_it_is"] = (
            f"{tool['client_description']} — your existing tool, received from your "
            f"previous supplier. Condition on arrival: "
            f"{tool['arrival_condition'] or 'not yet assessed'}.")
    return line


def lines_for(item_id, customer_id, quantity, landed_unit_cents, strategy="lowest_cost"):
    """Every Tooling Line for an item under one strategy."""
    treatment = STRATEGY_TREATMENTS.get(strategy, "amortized")
    return [line_for(t, quantity, landed_unit_cents, treatment)
            for t in tools_for_item(item_id, customer_id)]


def register_rows():
    """The tool register (§11.3.2). Admin-only: it carries location and condition."""
    return query(
        "SELECT t.*, i.sku, i.name AS item_name, c.company_name, c.ref AS customer_ref "
        "FROM tools t "
        "LEFT JOIN catalog_items i ON i.id = t.item_id "
        "JOIN customers c ON c.id = t.customer_id ORDER BY t.ref")
