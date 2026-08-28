"""The catalogue: what everyone may see, and what only one member may buy.

The previous specification said there was no catalogue and never would be. §8
reverses that. Everyone — signed in or not — can see example items with a
pricing *range*. What is gated is not looking. It is buying.

The shape of this module is the safety property. §8.2 lists what may never
appear in a public response: a negotiated price, a customer id or name, an
assignment record, an MOQ or lead time belonging to an assignment, any internal
cost field. The reliable way to keep that true as the code changes is not to
remember it at each call site — it is to make the public payload a different
function over a different query, so a negotiated price has no route into it. So:

    public_item()      reads catalog_items only. It cannot see a registration,
                       because it never joins one.
    registration_for() reads the registration for exactly one customer.
    member_item()      composes the two, and is only ever called with a
                       customer in hand.

§8.6 is the same idea in the other direction: the public range is entered by an
admin on the item, and is never derived from any customer's negotiated price. A
member's price sitting outside the published range is expected, not an error.
"""
from .db import query

# The six fields a public viewer gets, and nothing else. A08 asserts that a
# public payload's keys are a subset of this set, so adding a field to the
# public catalogue is a deliberate act that fails a check until it is reviewed.
PUBLIC_FIELDS = frozenset({
    "id", "sku", "name", "category", "description",
    "range_low_cents", "range_high_cents", "typical_moq",
    "typical_lead_time_days", "range_drivers", "images",
})

# Anything matching these must never appear in a public payload, by key or by
# value. Named here so A08 has something to assert against rather than a list
# that lives only in a reviewer's head.
FORBIDDEN_PUBLIC_KEYS = (
    "unit_price_cents", "custom_price_cents", "customer_id", "customer",
    "company_name", "assigned_by", "assigned_at", "matrix_id", "negotiated",
    "internal_cost_cents", "internal_notes", "cost_cents", "moq_negotiated",
)


def public_item(row):
    """One catalogue item as an anonymous visitor sees it.

    Reads only from `catalog_items`. There is no customer parameter and no join,
    so there is nothing customer-shaped available to leak.
    """
    return {
        "id": row["id"],
        "sku": row["sku"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "range_low_cents": row["range_low_cents"],
        "range_high_cents": row["range_high_cents"],
        "typical_moq": row["typical_moq"],
        "typical_lead_time_days": row["typical_lead_time_days"],
        "range_drivers": row["range_drivers"],
        "images": public_images(row["id"]),
    }


def public_items():
    rows = query(
        "SELECT * FROM catalog_items WHERE is_public = 1 AND is_active = 1 "
        "ORDER BY category, name")
    return [public_item(r) for r in rows]


def public_item_by_sku(sku):
    row = query(
        "SELECT * FROM catalog_items WHERE sku = ? AND is_public = 1 AND is_active = 1",
        (sku,), one=True)
    return public_item(row) if row else None


def public_images(item_id):
    """Images a visitor may see. A private image is not merely hidden — it is
    not selected, so there is no URL in the payload to try."""
    rows = query(
        "SELECT id, caption, source_label, alt_text, svg, stored_name, annotations "
        "FROM item_images WHERE item_id = ? AND is_public = 1 ORDER BY position, id",
        (item_id,))
    return [dict(r) for r in rows]


def item_images(item_id):
    """Every image on an item. Callers must already have established access."""
    rows = query(
        "SELECT id, caption, source_label, alt_text, svg, stored_name, annotations, is_public "
        "FROM item_images WHERE item_id = ? ORDER BY position, id", (item_id,))
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# registrations — the record that makes ordering possible
# --------------------------------------------------------------------------
def registration_for(customer_id, item_id):
    """The active registration binding this item to this customer, or None.

    `active = 1` is part of the query rather than something the caller checks
    afterwards, so a deactivated registration is indistinguishable from one that
    never existed — which is what WI-K-05 needs when a member tries to reorder
    from history.
    """
    if not customer_id or not item_id:
        return None
    return query(
        "SELECT * FROM catalogue_registrations "
        "WHERE customer_id = ? AND item_id = ? AND active = 1",
        (customer_id, item_id), one=True)


def registrations_for_customer(customer_id):
    if not customer_id:
        return []
    return query(
        "SELECT r.*, i.sku, i.name, i.category, i.description, i.image_url "
        "FROM catalogue_registrations r JOIN catalog_items i ON i.id = r.item_id "
        "WHERE r.customer_id = ? AND r.active = 1 AND i.is_active = 1 "
        "ORDER BY i.name", (customer_id,))


def registrations_for_item(item_id):
    """Admin-only. Who this item is registered to, and at what."""
    return query(
        "SELECT r.*, c.company_name, c.ref AS customer_ref "
        "FROM catalogue_registrations r JOIN customers c ON c.id = r.customer_id "
        "WHERE r.item_id = ? ORDER BY c.company_name", (item_id,))


def can_order(customer, item_id):
    """The single question order gating asks, at all three points (§8.4).

    Deliberately not "can they see it". A member may look at every public item
    in the catalogue; ordering needs a registration binding that item to them.
    """
    if customer is None:
        return False
    if (customer["membership_status"] or "") != "MEMBER":
        return False
    return registration_for(customer["id"], item_id) is not None


def price_for(customer_id, item_id, quantity=None, spec_tier=None):
    """What this member pays — their flat negotiated price, or a matrix cell.

    Returns (cents, input_id) so the caller can carry the provenance through to
    the rendered field. A number with no input id behind it is a P1 under §11.1,
    which is only checkable if the number arrives with its source attached.
    """
    reg = registration_for(customer_id, item_id)
    if reg is None:
        return None, None
    if reg["matrix_id"] and quantity:
        cell = matrix_cell(reg["matrix_id"], quantity, spec_tier)
        if cell:
            return cell["unit_price_cents"], cell["input_id"]
    if reg["unit_price_cents"] is not None:
        return reg["unit_price_cents"], None
    return None, None


def matrix_cell(matrix_id, quantity, spec_tier=None):
    """The cell covering this quantity at this spec tier, from a published matrix.

    Unpublished matrices are excluded in the query. §11.1 requires that nothing
    reaches a member before an admin publishes it deliberately, and a filter in
    the WHERE clause is harder to forget than a check in the caller.
    """
    matrix = query(
        "SELECT * FROM price_matrices WHERE id = ? AND published_at IS NOT NULL",
        (matrix_id,), one=True)
    if matrix is None:
        return None
    args = [matrix_id, quantity, quantity]
    sql = ("SELECT * FROM price_matrix_cells WHERE matrix_id = ? "
           "AND quantity_min <= ? AND (quantity_max IS NULL OR quantity_max >= ?)")
    if spec_tier:
        sql += " AND spec_tier = ?"
        args.append(spec_tier)
    sql += " ORDER BY quantity_min DESC LIMIT 1"
    return query(sql, tuple(args), one=True)


def matrix_grid(matrix_id):
    """The whole published matrix, as (tiers, quantity bands, cells) for rendering."""
    cells = query(
        "SELECT * FROM price_matrix_cells WHERE matrix_id = ? "
        "ORDER BY quantity_min, spec_tier", (matrix_id,))
    tiers, bands = [], []
    for c in cells:
        if c["spec_tier"] not in tiers:
            tiers.append(c["spec_tier"])
        band = (c["quantity_min"], c["quantity_max"])
        if band not in bands:
            bands.append(band)
    grid = {(c["quantity_min"], c["spec_tier"]): c for c in cells}
    return tiers, bands, grid


# --------------------------------------------------------------------------
# what the viewer is shown (§8.5)
# --------------------------------------------------------------------------
def cta_state(customer, item_id):
    """Which call to action this viewer gets. Five states, and no sixth.

    §8.5's rule is that no viewer ever sees an Order control they cannot use — a
    refused order after a visible Order button is a P1. That holds because this
    function and `can_order` ask the same question of the same table: the button
    renders on ORDER, and ORDER is returned on exactly the condition the
    server-side gate enforces.
    """
    if customer is None:
        return "ANONYMOUS"          # Apply for Membership, then Request a Quote
    status = customer["membership_status"] or ""
    if status == "PAUSED":
        return "PAUSED"             # say so, and what to do next — never a silent failure
    if status != "MEMBER":
        return "NOT_MEMBER"         # they can look; buying needs membership
    if registration_for(customer["id"], item_id) is None:
        return "REQUEST"            # Request this item — intake, pre-filled
    return "ORDER"


def range_text(item):
    """'$0.14 – $0.20 per unit', or an honest silence when no range is entered."""
    low, high = item.get("range_low_cents"), item.get("range_high_cents")
    if low is None or high is None:
        return None
    if low == high:
        return f"${low / 100:.2f}"
    return f"${low / 100:.2f} – ${high / 100:.2f}"
