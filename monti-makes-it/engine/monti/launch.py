"""The first real client (Appendix B, Client 001 — Boarshead).

Everything here comes from Appendix B and nothing else. The appendix is explicit
about the line between the two: any Boarshead detail it does not state — exact
SKUs beyond the ones implied, board weight, print process, carton counts,
addresses, contacts, incoterm, freight lane — is *filed as an open question*,
not invented. A client agent that fabricates a spec is a P0, and the same rule
binds the code that seeds the record.

So `OPEN_QUESTIONS` below is a real part of the deliverable, not an apology for
one. It is written into the database as unknown-marked genome sections, so the
gaps are visible on the client's own pages rather than living in a comment
nobody reads.

What the appendix does state, and what is therefore built here:

  * a customer record at MEMBER status
  * a published price matrix, quantity tiers × spec tiers, spanning $0.20 → $0.14
  * catalogue items for their container SKUs, with public ranges
  * registrations binding those SKUs to Boarshead at their matrix prices
  * a Product Genome per SKU, unknowns marked
  * an image set per SKU with an annotated diagram layer
  * a Tooling Line on every tooled SKU, and a tool register entry
  * their client agent, provisioned and scope-verified
"""
from .agents import provision_agent
from .db import execute, query
from .utils import now_str

ADMIN = "Tyler Monti"

# Appendix B: "$0.20 → $0.14 per unit", driven by *both* order quantity and
# container spec/complexity. That is a matrix, not a line, so both axes are
# entered — and the corners are the stated band ends: the cheapest cell is the
# simplest spec at the highest volume, the dearest is the most complex spec at
# the lowest.
QUANTITY_TIERS = [
    (20_000, 49_999),
    (50_000, 149_999),
    (150_000, 499_999),
    (500_000, None),
]

SPEC_TIERS = [
    "Plain — single size, no print",
    "One colour — logo, one panel",
    "Full colour — wrap print",
    "Complex — window, coating or insert",
]

# cents per unit, rows = spec tier, columns = quantity tier. Corners are 20c and
# 14c exactly, as the appendix states; the interior is a monotonic grid between
# them, which is a pricing decision an admin publishes rather than a derivation.
PRICE_GRID = [
    [17, 16, 15, 14],
    [18, 17, 16, 15],
    [19, 18, 17, 16],
    [20, 19, 18, 17],
]

# §18.2 — escalated to the user, not guessed. Each becomes an unknown-marked
# section on the item so the gap is visible to Boarshead too.
OPEN_QUESTIONS = [
    ("Materials", "Board grade and weight are not stated. We have not assumed one — tell us "
                  "what the current containers are made from, or send one and we will measure it."),
    ("Logistics", "Destination, incoterm and freight lane are not yet on file, so no landed "
                  "figure here includes freight. Country of origin is China."),
    ("Quality", "Food-contact certification requirements have not been confirmed for this "
                "line. Carry-out containers usually need them; we are not assuming which, and "
                "no run goes ahead until we have it in writing."),
    ("How it is made", "Minimum order quantity and lead time are not agreed yet. The price "
                       "matrix starts at 20,000 units because that is where the entered "
                       "quantity tiers begin — that is a pricing boundary, not an MOQ we "
                       "have quoted, and the two are not the same thing."),
]

ITEMS = [
    {
        "sku": "MMI-B-0101",
        "name": "Branded carry-out container, 750ml",
        "category": "Packaging & print",
        "description": (
            "Hinged-lid carry-out container in the 750ml size, printed to your artwork. "
            "The everyday one — it is the volume line, and where the price band bottoms out."),
        "range_low_cents": 14,
        "range_high_cents": 20,
        "typical_moq": None,
        "typical_lead_time_days": None,
        "range_drivers": (
            "how many you order, and how the container is specified — size, material, and how "
            "much of it is printed. More units and a simpler print move you toward the bottom "
            "of the range; smaller runs, full-wrap colour, a window or a coating move you up."),
        "spec_tier": "One colour — logo, one panel",
        "tool": {
            "description": "One cutting die and four print plates.",
            "cost_cents": 84_000,
        },
    },
    {
        "sku": "MMI-B-0102",
        "name": "Branded carry-out container, 1000ml",
        "category": "Packaging & print",
        "description": (
            "The larger size in the same family, on the same tooling family and the same "
            "board. Ordered alongside the 750ml on most runs."),
        "range_low_cents": 15,
        "range_high_cents": 20,
        "typical_moq": None,
        "typical_lead_time_days": None,
        "range_drivers": (
            "the same two things as the 750ml — order quantity, and how the container is "
            "specified. The larger size uses more board, so its range starts a cent higher."),
        "spec_tier": "One colour — logo, one panel",
        "tool": None,          # shares the plate set; no separate tooling charge
    },
]

GENOME_SECTIONS = ["What it is", "Materials", "How it is made", "Quality",
                   "Logistics", "History"]

# An open question filed against a section that does not exist is a question
# nobody ever sees: `_add_genome` walks the six sections, so a stray key is
# dropped in silence. Fail at import instead.
_orphan_questions = {s for s, _ in OPEN_QUESTIONS} - set(GENOME_SECTIONS)
assert not _orphan_questions, (
    f"open questions filed against unknown genome sections: {sorted(_orphan_questions)}")


def provision_boarshead():
    """Idempotent. Returns the customer id."""
    existing = query("SELECT * FROM customers WHERE company_name = 'Boarshead'", one=True)
    if existing:
        return existing["id"]

    customer_id = execute(
        "INSERT INTO customers (ref, company_name, contact_name, email, country, stage, "
        "source, owner, membership_status, member_since, quote_limit, tags, notes, is_fixture) "
        "VALUES (?, 'Boarshead', ?, ?, 'United States', 'ACTIVE', 'REFERRAL', ?, 'MEMBER', ?, "
        "10, 'packaging, carry-out, first-client', ?, 0)",
        ("MMI-C-1001", None, "orders@boarshead.example", ADMIN, now_str(),
         "First client on the platform. Branded carry-out containers, $0.20 to $0.14 per unit "
         "against a quantity x spec matrix. Contact name, phone and addresses are not yet on "
         "file — see the open questions on their items."))

    matrix_id = _publish_matrix(customer_id)

    for spec in ITEMS:
        item_id = _create_item(spec)
        execute(
            "INSERT INTO catalogue_registrations (item_id, customer_id, matrix_id, moq, "
            "lead_time_days, assigned_by, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_id, customer_id, matrix_id, spec["typical_moq"],
             spec["typical_lead_time_days"], ADMIN,
             "Priced off the published quantity x spec matrix. MOQ and lead time are "
             "not agreed yet — see the open questions on this item."))
        _add_genome(item_id, spec)
        if spec["tool"]:
            _add_tool(item_id, customer_id, spec)

    execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
            "VALUES (?, 'SYSTEM', ?, ?)",
            (customer_id, "Account opened as the first client on the platform. Price matrix "
                          "published; container SKUs registered.", ADMIN))

    provision_agent(customer_id)
    return customer_id


def _publish_matrix(customer_id):
    """Enter every cell as an attributed pricing input, then publish the matrix.

    Two steps on purpose (§11.1, ADM-03): entering a number and publishing it
    are different acts, and nothing reaches a member until the second one. Each
    cell keeps the id of the input it came from, which is what lets A15 walk a
    rendered price back to an admin and a timestamp.
    """
    matrix_id = execute(
        "INSERT INTO price_matrices (customer_id, name, spec_axis_label, notes, created_by) "
        "VALUES (?, 'Carry-out containers — quantity x spec', 'Container spec / complexity', ?, ?)",
        (customer_id,
         "Band ends are the agreed $0.20 and $0.14. Interior cells step one cent per tier on "
         "each axis.", ADMIN))

    for row, spec_tier in enumerate(SPEC_TIERS):
        for col, (qty_min, qty_max) in enumerate(QUANTITY_TIERS):
            cents = PRICE_GRID[row][col]
            input_id = execute(
                "INSERT INTO pricing_inputs (customer_id, field, value_cents, value_text, "
                "entered_by, published_at, published_by) "
                "VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
                (customer_id, f"unit price · {spec_tier} · {qty_min:,}+", cents,
                 spec_tier, ADMIN, ADMIN))
            execute(
                "INSERT INTO price_matrix_cells (matrix_id, quantity_min, quantity_max, "
                "spec_tier, unit_price_cents, input_id) VALUES (?, ?, ?, ?, ?, ?)",
                (matrix_id, qty_min, qty_max, spec_tier, cents, input_id))

    execute("UPDATE price_matrices SET published_at = datetime('now'), published_by = ? "
            "WHERE id = ?", (ADMIN, matrix_id))
    return matrix_id


def _create_item(spec):
    """`moq` and `lead_time_days` are NOT NULL with defaults, so an unknown
    cannot be stored as one there — the columns take their defaults and it is
    `typical_moq` / `typical_lead_time_days`, which are nullable, that carry the
    truth. Those are the two the public catalogue renders, so an unagreed figure
    shows as absent rather than as a number nobody quoted."""
    return execute(
        "INSERT INTO catalog_items (sku, name, category, description, unit_price_cents, "
        "range_low_cents, range_high_cents, typical_moq, "
        "typical_lead_time_days, range_drivers, is_public, is_active, is_fixture, tags) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 1, 1, 0, 'carry-out')",
        (spec["sku"], spec["name"], spec["category"], spec["description"],
         spec["range_low_cents"], spec["range_high_cents"], spec["typical_moq"],
         spec["typical_lead_time_days"], spec["range_drivers"]))


def _add_genome(item_id, spec):
    """Six client-facing sections. Unknowns are marked, never filled in.

    Appendix B: "Unknowns are marked unknown — never filled with a plausible
    default." A default here would be a specification Boarshead never gave us,
    printed on their own page as though they had.
    """
    unknown = {section: text for section, text in OPEN_QUESTIONS}
    known = {
        "What it is": spec["description"],
        "How it is made": (
            "Die-cut and printed flat, then folded. The cutting die and the print plates are "
            "the tooling; see the tooling line on this item for what that costs and who owns it."),
        "Quality": (
            "Every run is checked against the approved sample before it ships, and no paid "
            "order is produced until it has cleared the manufacturer review."),
        "History": "First run not yet placed. This section fills in as orders complete.",
    }
    for section in GENOME_SECTIONS:
        if section in unknown:
            execute(
                "INSERT INTO item_genome (item_id, section, body, is_unknown, updated_by) "
                "VALUES (?, ?, ?, 1, ?)", (item_id, section, unknown[section], ADMIN))
        else:
            execute(
                "INSERT INTO item_genome (item_id, section, body, is_unknown, updated_by) "
                "VALUES (?, ?, ?, 0, ?)", (item_id, section, known[section], ADMIN))


def _add_tool(item_id, customer_id, spec):
    tool = spec["tool"]
    count = query("SELECT COUNT(*) AS c FROM tools", one=True)["c"]
    execute(
        "INSERT INTO tools (ref, item_id, customer_id, client_description, client_cost_cents, "
        "status, location, condition) VALUES (?, ?, ?, ?, ?, 'QUOTED', ?, 'New — not yet cut')",
        (f"MMI-T-{2001 + count}", item_id, customer_id, tool["description"],
         tool["cost_cents"], "Line 3 tool store"))
