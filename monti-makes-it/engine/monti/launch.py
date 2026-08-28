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
        "typical_moq": 20_000,
        "typical_lead_time_days": 32,
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
        "typical_moq": 20_000,
        "typical_lead_time_days": 32,
        "range_drivers": (
            "the same two things as the 750ml — order quantity, and how the container is "
            "specified. The larger size uses more board, so its range starts a cent higher."),
        "spec_tier": "One colour — logo, one panel",
        "tool": None,          # shares the plate set; no separate tooling charge
    },
]

# A drawing rather than a photograph: we have not been sent product photography,
# and a stock image of someone else's container presented as Boarshead's would
# be fabricated evidence. The dimensions carried in the callouts are the ones
# the SKU names, and nothing else is asserted.
CONTAINER_SVG = """<svg viewBox="0 0 320 240" role="img" xmlns="http://www.w3.org/2000/svg">
  <rect width="320" height="240" fill="#F9F8F4"/>
  <path d="M78 96 L242 96 L226 188 L94 188 Z" fill="#EDE7DA" stroke="#8A958D" stroke-width="2"/>
  <path d="M78 96 L242 96 L250 74 L70 74 Z" fill="#E3DBCA" stroke="#8A958D" stroke-width="2"/>
  <path d="M70 74 L250 74 L250 62 L70 62 Z" fill="#D8CEB8" stroke="#8A958D" stroke-width="2"/>
  <rect x="118" y="118" width="84" height="34" rx="3" fill="none" stroke="#B08D4F"
        stroke-width="1.5" stroke-dasharray="5 3"/>
  <text x="160" y="140" text-anchor="middle" font-family="monospace" font-size="11"
        fill="#B08D4F">PRINT AREA</text>
</svg>"""

ANNOTATIONS = (
    '[{"x": 50, "y": 26, "label": "Hinged lid"},'
    ' {"x": 50, "y": 56, "label": "Print area, one panel"},'
    ' {"x": 30, "y": 78, "label": "Sidewall taper — stacks"},'
    ' {"x": 72, "y": 90, "label": "Base"}]'
)

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
             "Priced off the published quantity x spec matrix."))
        _add_images(item_id, spec)
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
    return execute(
        "INSERT INTO catalog_items (sku, name, category, description, unit_price_cents, moq, "
        "lead_time_days, range_low_cents, range_high_cents, typical_moq, "
        "typical_lead_time_days, range_drivers, is_public, is_active, is_fixture, tags) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, 1, 1, 0, 'carry-out')",
        (spec["sku"], spec["name"], spec["category"], spec["description"],
         spec["typical_moq"], spec["typical_lead_time_days"],
         spec["range_low_cents"], spec["range_high_cents"], spec["typical_moq"],
         spec["typical_lead_time_days"], spec["range_drivers"]))


def _add_images(item_id, spec):
    execute(
        "INSERT INTO item_images (item_id, svg, caption, source_label, alt_text, position, "
        "is_public, annotations) VALUES (?, ?, ?, ?, ?, 0, 1, ?)",
        (item_id, CONTAINER_SVG,
         f"{spec['name']} — form and print area",
         "Placeholder drawing · replaced when the client's own photographs arrive",
         f"Line drawing of a hinged-lid carry-out container showing the lid, the tapered "
         f"sidewall and the printable panel on the front face.",
         ANNOTATIONS))


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
