"""Who can see which catalog item.

Two ways an item reaches a member's portal:

  a tag       — the item carries tags, the member carries tags, and any overlap
                grants access. One tag can open a whole range to a whole segment
                of members at once, and a member can hold as many tags as you like.
  an assignment — a direct, per-member grant, optionally at a price and MOQ
                negotiated for that account alone.

A direct assignment always wins on price: if an item reaches someone both ways,
the negotiated number is the one they see.
"""
from .db import query


def parse_tags(raw):
    """'Bags, Leather ,bags' -> ['bags', 'leather'] — lowercased, de-duped, ordered."""
    if not raw:
        return []
    seen, out = set(), []
    for part in str(raw).replace(";", ",").split(","):
        tag = " ".join(part.split()).lower()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def format_tags(tags):
    return ", ".join(parse_tags(tags) if isinstance(tags, str) else tags)


def _col(row, name):
    try:
        return row[name]
    except (IndexError, KeyError):
        return None


def items_for_customer(customer, include_inactive=False):
    """Every item this member can see, with the price they'd pay and why they have it."""
    if customer is None:
        return []
    member_tags = set(parse_tags(_col(customer, "catalog_tags")))

    rows = query(
        "SELECT i.*, a.unit_price_cents AS custom_price_cents, a.moq AS custom_moq, "
        "       a.notes AS assign_note, a.assigned_at "
        "FROM catalog_items i "
        "LEFT JOIN catalogue_registrations a "
        "       ON a.item_id = i.id AND a.customer_id = ? AND a.active = 1 "
        + ("" if include_inactive else "WHERE i.is_active = 1 ")
        + "ORDER BY i.name", (customer["id"],))

    out = []
    for r in rows:
        assigned = r["assigned_at"] is not None
        item_tags = set(parse_tags(_col(r, "tags")))
        matched = sorted(member_tags & item_tags)
        if not assigned and not matched:
            continue
        out.append({
            "row": r,
            "id": r["id"], "sku": r["sku"], "name": r["name"], "category": r["category"],
            "description": r["description"], "materials": r["materials"], "specs": r["specs"],
            "lead_time_days": r["lead_time_days"], "image_url": r["image_url"],
            "list_price_cents": r["unit_price_cents"],
            "price_cents": r["custom_price_cents"] if r["custom_price_cents"] is not None
                           else r["unit_price_cents"],
            "moq": r["custom_moq"] or r["moq"],
            "note": r["assign_note"],
            "negotiated": r["custom_price_cents"] is not None,
            "via_assignment": assigned,
            "matched_tags": matched,
            "item_tags": sorted(item_tags),
        })
    return out


def can_customer_see(customer, item_id):
    return any(i["id"] == item_id for i in items_for_customer(customer))


def customers_for_item(item):
    """Which members an item reaches, and how. Used on the catalog page."""
    item_tags = set(parse_tags(_col(item, "tags")))
    rows = query(
        "SELECT c.*, a.unit_price_cents AS custom_price_cents, a.moq AS custom_moq, "
        "       a.notes AS note, a.assigned_at "
        "FROM customers c LEFT JOIN catalogue_registrations a "
        "ON a.customer_id = c.id AND a.item_id = ? AND a.active = 1 "
        "ORDER BY c.company_name", (item["id"],))
    out = []
    for r in rows:
        matched = sorted(set(parse_tags(_col(r, "catalog_tags"))) & item_tags)
        if r["assigned_at"] is None and not matched:
            continue
        out.append({"row": r, "matched_tags": matched,
                    "via_assignment": r["assigned_at"] is not None})
    return out


def all_tags():
    """Every tag in use, with how many items and members carry it."""
    counts = {}
    for r in query("SELECT tags FROM catalog_items WHERE is_active = 1"):
        for t in parse_tags(_col(r, "tags")):
            counts.setdefault(t, {"tag": t, "items": 0, "members": 0})["items"] += 1
    for r in query("SELECT catalog_tags FROM customers"):
        for t in parse_tags(_col(r, "catalog_tags")):
            counts.setdefault(t, {"tag": t, "items": 0, "members": 0})["members"] += 1
    return sorted(counts.values(), key=lambda x: (-x["items"], x["tag"]))
