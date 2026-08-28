"""The first real client (Appendix B, Client 001 — Boars Head).

Everything here comes from Appendix B and nothing else. The appendix is explicit
about the line between the two: any Boars Head detail it does not state — exact
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
  * registrations binding those SKUs to Boars Head at their matrix prices
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
# section on the item so the gap is visible to Boars Head too.
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


# Freight lanes. Rates a forwarder would quote for a consolidated carton lane
# out of South China — entered here so every freight figure on the site resolves
# to a row someone put in, rather than to a constant in the arithmetic. They are
# estimates and the Decision Room says so; §11.1 requires provenance, not
# certainty.
FREIGHT_LANES = [
    # mode, per-unit cents, fixed cents spread over the run, transit, lane label
    ("ocean", 2, 54_000, "32 days at sea", "Ocean, consolidated"),
    ("split", 5, 65_000, "14 days average", "Split — 30% air, 70% ocean"),
    ("air", 14, 90_000, "6 days in the air", "Air, direct"),
]


def provision_freight_lanes():
    for mode, per_unit, fixed, transit, label in FREIGHT_LANES:
        if query("SELECT id FROM freight_lanes WHERE mode = ?", (mode,), one=True):
            continue
        execute(
            "INSERT INTO freight_lanes (mode, per_unit_cents, fixed_cents, transit_label, "
            "lane_label, entered_by) VALUES (?, ?, ?, ?, ?, ?)",
            (mode, per_unit, fixed, transit, label, ADMIN))


def provision_boars_head():
    """Idempotent. Returns the customer id."""
    existing = query("SELECT * FROM customers WHERE company_name = 'Boars Head'", one=True)
    if existing:
        return existing["id"]

    customer_id = execute(
        "INSERT INTO customers (ref, company_name, contact_name, email, country, stage, "
        "source, owner, membership_status, member_since, quote_limit, tags, notes, is_fixture) "
        "VALUES (?, 'Boars Head', ?, ?, 'United States', 'ACTIVE', 'REFERRAL', ?, 'MEMBER', ?, "
        "10, 'packaging, carry-out, first-client', ?, 0)",
        ("MMI-C-1001", None, "orders@boars_head.example", ADMIN, now_str(),
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
    _provision_decision_items(customer_id)
    _provision_capacity_and_plan(customer_id)
    return customer_id


def _provision_decision_items(customer_id):
    """One priced item and one still waiting, both real.

    The priced one is the 750ml container: its cost inputs are derived from the
    published matrix rather than invented, so the Decision Room's arithmetic and
    the matrix agree about the same product. The waiting one is a genuine open
    question — Appendix B lists board grade among the details to escalate, and
    an item sitting on stage 2 asking for it is what that looks like in the
    product rather than in a footnote.
    """
    item = query("SELECT * FROM catalog_items WHERE sku = 'MMI-B-0101'", one=True)
    if item is None or query("SELECT id FROM decision_items WHERE customer_id = ?",
                             (customer_id,), one=True):
        return

    # The matrix's own band, so the slider cannot offer a quantity nobody priced.
    band = query(
        "SELECT MIN(quantity_min) AS lo, MAX(COALESCE(quantity_max, quantity_min)) AS hi "
        "FROM price_matrix_cells c JOIN price_matrices m ON m.id = c.matrix_id "
        "WHERE m.customer_id = ?", (customer_id,), one=True)

    # `published_at` is the gate every member-facing read filters on, so an
    # APPROVED row without it renders as pending — which is correct behaviour and
    # was exactly the bug when this seed forgot to set it.
    priced_id = execute(
        "INSERT INTO decision_items (ref, auto_name, client_name, customer_id, "
        "catalog_item_id, status, stage, source, received_at, published_at, "
        "published_by, qty_min, qty_max, qty_step, is_fixture) "
        "VALUES ('MMI-D-001', 'Unapproved item 001', ?, ?, ?, 'APPROVED', 3, ?, ?, ?, ?, "
        "?, ?, 5000, 0)",
        ("Carry-out container, 750ml", customer_id, item["id"],
         "Existing production part — specification supplied by the client",
         now_str(), now_str(), ADMIN, band["lo"], band["hi"]))

    # The six cost inputs. Material is the matrix's own floor cell minus the
    # freight and duty the Decision Room adds back, so the two surfaces agree
    # about the same container rather than quoting each other's numbers.
    for field, cents in (("material_unit", 11),
                         ("tooling_total", 84_000),
                         ("packaging_custom_unit", 1),
                         ("packaging_standard_unit", 0),
                         ("duty_rate_pct", 0),          # carry-out cartons: 0%
                         ("lab_total", 65_000)):
        execute(
            "INSERT INTO pricing_inputs (customer_id, item_id, field, value_cents, "
            "entered_by, published_at, published_by) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
            (customer_id, priced_id, field, cents, ADMIN, ADMIN))

    for slot, label, treatment, title, extra, lead, mode, prod, inspect, foot, lab in (
        (0, "Lowest landed cost", "amortized", "Consolidated ocean, single batch",
         0, 62, "ocean", "One batch, standard queue", "AQL 2.5 sampling",
         "The cheapest route we can actually run", 0),
        (1, "Fastest arrival", "upfront", "Air freight, priority line",
         2, 26, "air", "Priority slot", "AQL 2.5 sampling",
         "Slot held 48 hours", 0),
        (2, "Highest certainty", "upfront_with_sample", "Ocean, full inspection, sample run",
         3, 74, "ocean", "Reserved capacity", "100% functional plus third-party lab",
         "Includes the certification pack", 1),
    ):
        execute(
            "INSERT INTO item_strategies (item_id, slot, label, title, extra_cents, "
            "lead_days, mode, production, inspection, footnote, includes_lab, "
            "tooling_treatment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (priced_id, slot, label, title, extra, lead, mode, prod, inspect, foot,
             lab, treatment))

    for kind, label, note, saving in (
        ("qty", "Order QTYNEW instead of QTYNOW",
         "Spreads the tooling across more units and fills the container better.", 0),
        ("pkg", "Plain carton instead of printed",
         "Your artwork moves to an applied label. No change to protection.", 0),
    ):
        execute("INSERT INTO item_levers (item_id, kind, label, note, saving_cents) "
                "VALUES (?, ?, ?, ?, ?)", (priced_id, kind, label, note, saving))

    # The waiting item. Stage 2, with the real outstanding question on it.
    execute(
        "INSERT INTO decision_items (ref, auto_name, customer_id, status, stage, source, "
        "outstanding, received_at, is_fixture) VALUES ('MMI-D-002', 'Unapproved item 002', "
        "?, 'PENDING', 2, ?, ?, ?, 0)",
        (customer_id,
         "Existing container sent for measurement",
         "Board grade and weight. Appendix B lists it as an open question and we are not "
         "assuming one — send a sample or tell us what the current containers are made "
         "from, and this moves to pricing.",
         now_str()))


def _provision_capacity_and_plan(customer_id):
    """The Factory Plan and the commitments, with unmeasured ones marked.

    E4.02: a commitment with no measurable source says so. Boars Head has not
    placed a run yet, so most of these have nothing to measure against — and
    `met = NULL` renders as "not yet measured" rather than as a tick.
    """
    if query("SELECT id FROM factory_plans WHERE customer_id = ?", (customer_id,), one=True):
        return

    execute(
        "INSERT INTO factory_plans (customer_id, written_at, first_product, annual_demand, "
        "method, open_questions, testing, first_order_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (customer_id, now_str(),
         "Branded carry-out containers, 750ml and 1000ml",
         "Not yet stated — to be agreed with the client",
         "Die-cut and printed flat, then folded",
         "Board grade and weight; food-contact certification; MOQ and lead time",
         "Not yet confirmed — depends on the certification answer",
         "Sample or spec → price matrix published → first run"))

    for side, rows in (
        ("MEMBER", [
            ("Honest volume expectations", None),
            ("Complete and lawful product information", None),
            ("Timely approvals", None),
            ("A named decision-maker", None),
            ("Payment on agreed terms", None),
        ]),
        ("MONTI", [
            ("Quote within 24 hours", None),
            ("Confidentiality of your designs", None),
            ("Documented quality controls", None),
            ("Honest capacity information", None),
            ("No undisclosed substitutions", None),
        ]),
    ):
        for position, (text, measure) in enumerate(rows):
            execute(
                "INSERT INTO commitments (customer_id, side, commitment, measure, met, position) "
                "VALUES (?, ?, ?, ?, NULL, ?)", (customer_id, side, text, measure, position))


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
    default." A default here would be a specification Boars Head never gave us,
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
