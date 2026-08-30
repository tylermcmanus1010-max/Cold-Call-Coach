"""One list. Everything this member has asked us to make, or can order from us.

There were two tabs, and they were the same object at different ages.

    My products  read `decision_items` — a thing the member asked for, at stage
                 1, 2 or 3, with a Decision Room once it was priced. No way to
                 buy it.

    My catalog   read `catalog_items` through the registrations that bind a line
                 to an account — a thing we already make for them, orderable.
                 No history, no stage, no room.

A product does not change identity when it crosses that line. It is described
badly, it gets specified, it gets priced, and then it can be bought; splitting
the last step onto its own tab meant a member watching an item move had to
notice it had vanished from one list and appeared in another. The column that
joins them already existed — `decision_items.catalog_item_id` — and nothing
read it.

So there is one list here and both old routes render it. What a row can do is a
property of the row, not of which page you happened to open.

TENANCY, which is the whole risk in a merge like this

Two lists means two scoping rules, and joining them is exactly where the looser
one wins by accident. The rules do not merge:

  - decision_items are scoped by `customer_id = ?` in SQL. Nothing else.
  - the catalogue half is taken ONLY from `catalog.items_for_customer(customer)`,
    which applies registrations and tags. It is never fetched by following
    `decision_items.catalog_item_id`, even though that column is right there and
    the join would be one line shorter.

The difference matters when the two disagree. If a member's item points at a
catalogue line that is not registered to them — a registration deactivated, an
admin mistake, a line moved to another account — following the column would put
another account's product name, price and MOQ on this member's screen. Reading
the visible set instead means the row renders as a product with no orderable
half, which is what it is. `unlinked()` reports that case so it is visible as a
defect rather than absorbed silently. A39 proves it.

PRICE

`catalog.items_for_customer` returns a `price_cents` that is the flat negotiated
price or the list price. For a matrix-priced registration both are null, and the
old catalogue template read keys that function does not return at all, so every
card rendered "$0.00" under a badge asserting it was that member's negotiated
price. A price of zero with no input behind it is a §11.1 P1, and asserting it
is negotiated makes it worse.

Prices here come from `catalogue.price_for`, which returns (cents, input_id) so
the number arrives with its provenance attached. Where a matrix prices by
quantity, that is stated as a from-price at a named quantity rather than
flattened to one figure — the Decision Room is where the quantity is chosen, and
this list links into it rather than pretending to answer.
"""
from . import catalog as catalog_mod
from . import catalogue
from .db import query

# Stage 3 is "priced — awaiting release", not "on sale": published_at is the gate.
STAGES = ["Received", "Specification in review", "Priced — awaiting release"]

IN_PROGRESS = "in_progress"     # asked for, no price a member can act on
PRICED = "priced"               # a Decision Room exists; no orderable line yet
ORDERABLE = "orderable"         # a registered catalogue line: it can be bought


def _decision_rows(customer_id):
    return query(
        "SELECT * FROM decision_items WHERE customer_id = ? ORDER BY received_at DESC",
        (customer_id,))


def _price(customer, entry):
    """(cents, input_id, basis, quantity) for a catalogue entry this member can see.

    `quantity` is the number the figure applies at, which for a matrix is not the
    MOQ — see `catalogue.matrix_floor`.

    `basis` is what the number means, and it is returned rather than inferred by
    the template because "which kind of price is this" decides the wording and
    getting it wrong is how "$0.00 · Your price" happened.

      "negotiated"  a flat price agreed with this member
      "matrix"      a published quantity band; the figure is a FROM price at the
                    quantity named alongside it, and changes with quantity
      "list"        the catalogue's own price, no registration price set
      None          no price exists — say so, never show zero
    """
    item_id = entry["id"]
    reg = catalogue.registration_for(customer["id"], item_id)
    if reg is None:
        return None, None, None, None
    quantity = entry.get("moq") or 1
    if reg["matrix_id"]:
        cents, input_id = catalogue.price_for(customer["id"], item_id, quantity=quantity)
        if cents is not None:
            return cents, input_id, "matrix", quantity
        # The MOQ is below everything the desk priced. Quote the floor instead of
        # reporting no price: sixteen published cells exist, and "not priced yet"
        # about an item with a published matrix behind it is as wrong as a made-up
        # number, just in the other direction. The quantity travels with the
        # figure so it reads as "from 17c at 20,000", never as a unit price.
        floor = catalogue.matrix_floor(reg["matrix_id"])
        if floor is not None:
            return floor["unit_price_cents"], floor["input_id"], "matrix", \
                   floor["quantity_min"]
    if reg["unit_price_cents"] is not None:
        return reg["unit_price_cents"], None, "negotiated", quantity
    if entry.get("list_price_cents"):
        return entry["list_price_cents"], None, "list", quantity
    return None, None, None, None


def for_member(customer):
    """Every product this member has, newest first, each row saying what it can do.

    A row is one product. It carries the decision item, the orderable catalogue
    line, or both — and `state` says which, so no template has to work it out
    from the presence of a key.
    """
    if customer is None:
        return []

    visible = {e["id"]: e for e in catalog_mod.items_for_customer(customer)}
    rows, claimed = [], set()

    for item in _decision_rows(customer["id"]):
        # The linked catalogue line, but only if this member can actually see it.
        entry = visible.get(item["catalog_item_id"]) if item["catalog_item_id"] else None
        if entry is not None:
            claimed.add(entry["id"])
        rows.append(_row(customer, item=item, entry=entry))

    # Catalogue lines with no product behind them. Boars Head's 1000ml container
    # is one: registered to the account without ever having come through the
    # door. Not a defect, and not hidden either — a member who can order it has
    # to be able to find it.
    for entry in visible.values():
        if entry["id"] not in claimed:
            rows.append(_row(customer, item=None, entry=entry))

    order = {ORDERABLE: 0, PRICED: 1, IN_PROGRESS: 2}
    rows.sort(key=lambda r: (order[r["state"]], (r["name"] or "").lower()))
    return rows


def _row(customer, item, entry):
    cents = input_id = basis = at_quantity = None
    orderable = False
    if entry is not None:
        orderable = catalogue.can_order(customer, entry["id"])
        cents, input_id, basis, at_quantity = _price(customer, entry)

    if orderable:
        state = ORDERABLE
    elif item is not None and item["status"] == "APPROVED" and item["published_at"]:
        state = PRICED
    else:
        state = IN_PROGRESS

    if item is not None:
        name = item["client_name"] or (entry["name"] if entry else None) or item["auto_name"]
        ref = item["ref"]
    else:
        name = entry["name"]
        ref = entry["sku"]

    return {
        "ref": ref, "name": name, "state": state,
        "item": item, "entry": entry,
        "orderable": orderable,
        "price_cents": cents, "price_input_id": input_id, "price_basis": basis,
        "price_quantity": at_quantity,
        # What a member may actually order. A catalogue MOQ of 1 under a matrix
        # priced from 20,000 would let them place an order at a quantity nothing
        # has a price for, so the floor wins where it is higher.
        "min_quantity": max(entry.get("moq") or 1, at_quantity or 1) if entry else None,
        # Named by the member, or still carrying the number it arrived with.
        "unnamed": item is not None and not item["client_name"],
        "stage_label": (STAGES[item["stage"] - 1]
                        if item is not None and 1 <= item["stage"] <= len(STAGES) else None),
        "priced_at": item["published_at"] if item is not None else None,
        "sku": entry["sku"] if entry else None,
        "item_id": entry["id"] if entry else None,
        "moq": entry.get("moq") if entry else None,
        "lead_time_days": entry.get("lead_time_days") if entry else None,
    }


def unlinked(customer):
    """Products pointing at a catalogue line this member cannot see.

    Always a defect, and a quiet one: the merged list renders the product with
    no orderable half, which looks exactly like a product that was never
    catalogued. The alternative — following `catalog_item_id` and rendering
    whatever it returns — would put another account's name and price on this
    member's screen, so the list is right to drop it and wrong to say nothing.
    """
    visible = {e["id"] for e in catalog_mod.items_for_customer(customer)}
    return [item for item in _decision_rows(customer["id"])
            if item["catalog_item_id"] and item["catalog_item_id"] not in visible]
