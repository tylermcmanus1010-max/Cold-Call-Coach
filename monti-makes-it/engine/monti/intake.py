"""One door. Every request a member makes, however it arrives.

There used to be two of these, and they did not know about each other.

    The public quote form wrote a `quotes` row — a reference, a 24-hour clock, a
    quota debit, an estimate to accept or decline — and no product.

    "Describe it badly" in the portal wrote a `decision_items` row — a product
    with a stage tracker and, once priced, a Decision Room — and no quote, so no
    clock and no quota debit.

Both are the same act: a member asking us to make something. Splitting it in two
did not just duplicate a form, it split the accounting. `membership.quota_state`
counts rows in `quotes`; `genome.capacity` sums weights in `capacity_ledger`;
both measure the same allowance, and each was blind to whatever the other door
created. A member could open a request the counter never saw.

So there is one function here and both doors call it. Not a shared helper the
callers may skip — the only path that writes a request, which is why neither
blueprint inserts into `quotes` or `decision_items` any more. `A37` proves the
two records exist and are linked, and that breaking the link is caught.

What one submission produces, in one transaction's worth of work:

  a `quotes` row          the reference the member quotes at us, the SLA clock,
                          and the record the pricing desk works from
  a `decision_items` row  the product, at stage 1, linked back by `quote_id`,
                          carrying no price because nobody has signed a spec
  a `capacity_ledger` row the weighted debit, recorded with the request so the
                          header and the rows cannot disagree (E4.04)
  a CRM activity          so the account timeline shows it
  a calendar deadline     so the SLA is a date something watches, not a promise

The order matters in one place only: the capacity row wants both foreign keys,
so it is written last.
"""
from flask import current_app

from .db import execute, next_ref, query
from .utils import plus_hours, to_int

# §MEM-06 — the weight a request consumes is decided by the engineering it takes,
# not by counting requests. A member picks one and sees it before sending; if we
# classify it differently we say so in the ledger, with the reason.
WEIGHTS = [
    ("variation", 1, "A change to something we already make for you"),
    ("new", 2, "A new product — one part, one process"),
    ("assembly", 4, "A complex assembly — several parts, tooling, or sub-suppliers"),
]

# The formats the door accepts. Each carries what happens to that kind of thing,
# because the reason people do not send a voice note is that they assume it is
# not usable — the list is an answer to "will you even take this?", not a picker.
FORMATS = [
    ("Voice note", "A transcript, then a structured feature list you confirm. "
                   "Most members do this from the floor."),
    ("Phone video", "We pull still frames, identify construction, and mark what we "
                    "still need to see."),
    ("Sketch", "We redraw it to scale and send it back with the assumptions we made "
               "highlighted."),
    ("Photo with something for scale", "Put a coin, a ruler or a caliper in frame and "
                                       "we can scale the whole part from it."),
    ("A competitor's listing", "We treat the listing as a requirements document, not a "
                               "target to copy."),
    ("Your current supplier's quote", "We normalise it into a true landed cost and show "
                                      "you every line it left out."),
    ("CAD or a drawing", "STEP, IGES, DXF or PDF go straight to a manufacturability "
                         "review."),
    ("The thing itself", "Ask for a Make This Box. Prepaid, tamper-evident, and tracked "
                         "from the moment it leaves your hands."),
]

WEIGHT_VALUES = {w for _, w, _ in WEIGHTS}
DEFAULT_WEIGHT = 2


def classify(weight):
    """The weight class in words, for the ledger row and the member's receipt."""
    return next((label for _, w, label in WEIGHTS if w == weight),
                "New product")


def create_request(customer, *, title, description, source=None, weight=DEFAULT_WEIGHT,
                   author="portal", **quote_fields):
    """Record one request. Returns (quote_row, item_row).

    `quote_fields` are the optional specification columns on `quotes` —
    category, quantity, materials, destination and so on. They are passed
    straight through, so the long public form and the four rough questions in
    the portal write the same row with different amounts of it filled in. A
    field nobody answered stays NULL rather than being invented.
    """
    weight = weight if weight in WEIGHT_VALUES else DEFAULT_WEIGHT
    sla = current_app.config["QUOTE_SLA_HOURS"]

    q_ref = next_ref("MMI-Q", "quotes", start=1001)
    quote_id = execute(
        "INSERT INTO quotes (ref, customer_id, title, description, category, quantity, "
        "quantity_unit, target_unit_price_cents, materials, dimensions, color_finish, "
        "packaging, certifications, destination_country, destination_city, incoterm, "
        "needed_by, priority, due_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (q_ref, customer["id"], title, description,
         quote_fields.get("category"), to_int(quote_fields.get("quantity"), 0),
         quote_fields.get("quantity_unit") or "units",
         quote_fields.get("target_unit_price_cents"),
         quote_fields.get("materials"), quote_fields.get("dimensions"),
         quote_fields.get("color_finish"), quote_fields.get("packaging"),
         quote_fields.get("certifications"), quote_fields.get("destination_country"),
         quote_fields.get("destination_city"), quote_fields.get("incoterm") or "DDP",
         quote_fields.get("needed_by"), quote_fields.get("priority") or "NORMAL",
         plus_hours(sla)))

    # The product. It exists from the moment the request does, which is the point
    # of the merge: a member watches one thing move rather than tracking a quote
    # reference here and a product there. It carries no price and cannot, because
    # `published_at` is null until an admin publishes (WI-I-03).
    count = query("SELECT COUNT(*) AS c FROM decision_items", one=True)["c"]
    d_ref = f"MMI-D-{count + 1:03d}"
    item_id = execute(
        "INSERT INTO decision_items (ref, auto_name, customer_id, quote_id, status, "
        "stage, source, outstanding, is_fixture) "
        "VALUES (?, ?, ?, ?, 'PENDING', 1, ?, ?, 0)",
        (d_ref, f"Unapproved item {count + 1:03d}", customer["id"], quote_id,
         source or "A written description",
         "Nothing yet. We will come back within 24 hours with a structured draft, "
         "and a named engineer signs it before it becomes a price."))

    # E4.04's fairness rule lives in `charged`: a declined or incomplete request
    # is reclassified to zero here rather than being deleted, so the member can
    # see it was not charged and why.
    execute(
        "INSERT INTO capacity_ledger (customer_id, quote_id, item_id, label, classified, "
        "weight, outcome, charged) VALUES (?, ?, ?, ?, ?, ?, 'In progress', ?)",
        (customer["id"], quote_id, item_id, title[:120], classify(weight), weight, weight))

    execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
            "VALUES (?, 'SYSTEM', ?, ?)",
            (customer["id"], f"Requested {q_ref} / {d_ref}: {title[:160]}", author))
    execute(
        "INSERT INTO calendar_events (title, customer_id, kind, starts_at, notes, created_by) "
        "VALUES (?, ?, 'DEADLINE', ?, ?, 'system')",
        (f"Quote due · {q_ref}", customer["id"], plus_hours(sla),
         f"{sla}h estimate deadline for {customer['company_name']}."))

    return (query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True),
            query("SELECT * FROM decision_items WHERE id = ?", (item_id,), one=True))


def orphans():
    """Requests with only half a record. The merge, made checkable.

    Two directions, and they are not symmetric.

      A quote with no product is always a defect. Nothing but this function
      writes a `quotes` row, so a quote that has no `decision_items` row
      pointing at it means the door wrote half a request.

      A product with no quote is only a defect if it came through the door.
      Boars Head's two items predate this path — they were migrated from an
      existing relationship, and inventing a quote reference and a 24-hour clock
      for them would be manufacturing history rather than recording it. What
      separates the two cases is decidable rather than a judgement: the door
      always writes a `capacity_ledger` row carrying both keys, so an item with
      a capacity row and no quote is the door failing, and an item with neither
      is a migration.
    """
    return {
        "quotes_without_item": query(
            "SELECT q.* FROM quotes q "
            "WHERE NOT EXISTS (SELECT 1 FROM decision_items d WHERE d.quote_id = q.id)"),
        "items_without_quote": query(
            "SELECT d.* FROM decision_items d "
            "JOIN capacity_ledger c ON c.item_id = d.id "
            "WHERE d.quote_id IS NULL AND d.is_fixture = 0"),
        "migrated": query(
            "SELECT d.* FROM decision_items d WHERE d.quote_id IS NULL AND d.is_fixture = 0 "
            "AND NOT EXISTS (SELECT 1 FROM capacity_ledger c WHERE c.item_id = d.id)"),
    }
