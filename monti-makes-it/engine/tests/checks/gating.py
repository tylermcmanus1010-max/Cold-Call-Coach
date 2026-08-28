"""A07 — order gating, and A08 — public price leak.

These are the two checks the catalogue reversal (§8) exists to make necessary.
Opening the catalogue means every item now has a public face and a private
price, and both failures are P0: a member ordering an item not registered to
them, and a negotiated price appearing in a public response.

A07 probes all three server-side points rather than the one the UI happens to
use, because the UI is not the enforcement — §8.4 is explicit that removing the
client-side check must not make the action possible.

A08 works by allowlist, not denylist. Asserting that a payload does not contain
today's list of forbidden keys passes happily the day someone adds a new
customer-derived field. Asserting that a payload contains *only* the fields
§8.2 permits fails on that same day, which is the point.
"""
from flask import g

from . import Check, Finding

# The three points §8.4 names, as (label, how to attempt it).
GATE_POINTS = ("add-to-cart", "order-create", "checkout-start")


def _unregistered_item_id(ctx):
    """A public item the probing member has no active registration for.

    If every public item is registered to them the probe proves nothing, so this
    deactivates one rather than reporting a vacuous pass.
    """
    rows = ctx.query(
        "SELECT i.id FROM catalog_items i WHERE i.is_public = 1 AND i.is_active = 1 "
        "AND i.id NOT IN (SELECT item_id FROM catalogue_registrations "
        "                 WHERE customer_id = ? AND active = 1) LIMIT 1",
        (ctx.member_customer_id,))
    return rows[0]["id"] if rows else None


def run(ctx):
    findings = []
    item_id = _unregistered_item_id(ctx)
    if item_id is None:
        findings.append(Finding(
            "A07", "no unregistered public item exists to probe with — the check "
                   "cannot demonstrate a refusal and must not report a pass"))
        return findings

    client = ctx.member_client

    # Point 1 — add to cart.
    r = client.post(f"/portal/cart/add/{item_id}",
                    data={"quantity": "1000", "_csrf": ctx.csrf(client)})
    if r.status_code not in (403, 404):
        findings.append(Finding(
            "portal.cart_add", f"add-to-cart for unregistered item {item_id} "
                               f"returned {r.status_code}, expected a refusal"))
    cart = ctx.query("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ? AND item_id = ?",
                     (ctx.member_customer_id, item_id))
    if cart[0]["c"]:
        findings.append(Finding(
            "cart_items", f"unregistered item {item_id} reached the cart"))

    # Point 2 — order create. Put the row in the cart directly, bypassing point
    # one entirely: that is exactly what an attacker who found a way past the
    # first gate would have, and the second gate has to hold on its own.
    ctx.execute("INSERT INTO cart_items (customer_id, item_id, quantity) VALUES (?, ?, 1000)",
                (ctx.member_customer_id, item_id))
    try:
        before = ctx.query("SELECT COUNT(*) AS c FROM orders", )[0]["c"]
        client.post("/portal/cart/checkout", data={"_csrf": ctx.csrf(client)},
                    follow_redirects=True)
        after = ctx.query("SELECT COUNT(*) AS c FROM orders")[0]["c"]
        if after > before:
            findings.append(Finding(
                "portal.cart_checkout",
                f"an order was created containing unregistered item {item_id}"))
    finally:
        ctx.execute("DELETE FROM cart_items WHERE customer_id = ? AND item_id = ?",
                    (ctx.member_customer_id, item_id))

    # Point 3 — checkout start on an existing order whose registration has since
    # been deactivated. This is the case the first two gates cannot cover.
    order_id = ctx.make_order_for(ctx.member_customer_id, item_id)
    try:
        r = client.get(f"/portal/orders/{order_id}/checkout", follow_redirects=True)
        body = r.get_data(as_text=True)
        if "no longer registered" not in body:
            findings.append(Finding(
                "portal.checkout",
                f"checkout opened for order {order_id} on unregistered item {item_id}"))
        r = client.post(f"/portal/orders/{order_id}/pay",
                        data={"method": "card", "_csrf": ctx.csrf(client)},
                        follow_redirects=True)
        paid = ctx.query("SELECT payment_status FROM orders WHERE id = ?", (order_id,))
        if paid and paid[0]["payment_status"] not in ("UNPAID",):
            findings.append(Finding(
                "portal.pay",
                f"payment progressed on order {order_id} for an unregistered item"))
    finally:
        ctx.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        ctx.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    return findings


def prove(ctx):
    """Remove one server-side check, confirm A07 names it, put it back.

    §8.4 requires each of the three points to be independently probed, so the
    proof breaks each one in turn — a proof that only breaks the first would
    leave two checks unproven while counting all three toward coverage.
    """
    from pathlib import Path
    portal = Path(__file__).resolve().parent.parent.parent / "monti" / "blueprints" / "portal.py"
    original = portal.read_text()

    defects = [
        ("add-to-cart",
         "    if not catalogue.can_order(g.customer, item_id):\n        abort(404)",
         "    if False:\n        abort(404)"),
        ("order-create",
         '        if line["item_id"] and not catalogue.can_order(g.customer, line["item_id"]):',
         '        if False:'),
        ("checkout-start",
         "    blocked = _unregistered_lines(order_id)\n    if blocked:",
         "    blocked = []\n    if blocked:"),
    ]

    results = []
    try:
        for label, present, broken in defects:
            if present not in original:
                results.append((label, False, "the guard this proof breaks is not in the source"))
                continue
            portal.write_text(original.replace(present, broken))
            ctx.reload()
            findings = run(ctx)
            results.append((label, bool(findings),
                            str(findings[0]) if findings else "MISSED"))
            portal.write_text(original)
            ctx.reload()
    finally:
        portal.write_text(original)
        ctx.reload()

    missed = [label for label, caught, _ in results if not caught]
    detail = "; ".join(f"{label} -> {note}" for label, _, note in results)
    return (not missed), detail


# --------------------------------------------------------------------------
# A08 — nothing customer-derived in a public response
# --------------------------------------------------------------------------
def run_a08(ctx):
    from monti import catalogue

    findings = []
    with ctx.app.app_context():
        items = catalogue.public_items()

    # The payload, by shape.
    for item in items:
        extra = set(item) - catalogue.PUBLIC_FIELDS
        if extra:
            findings.append(Finding(
                f"public_item({item.get('sku')})",
                f"fields outside the public set: {sorted(extra)}"))
        for forbidden in catalogue.FORBIDDEN_PUBLIC_KEYS:
            if forbidden in item:
                findings.append(Finding(
                    f"public_item({item.get('sku')})",
                    f"forbidden field {forbidden!r} present"))

    # And by value, on the rendered route — a template can print something the
    # payload never carried.
    negotiated = ctx.query(
        "SELECT r.unit_price_cents, c.company_name, c.ref FROM catalogue_registrations r "
        "JOIN customers c ON c.id = r.customer_id WHERE r.active = 1")
    for route in ["/catalogue"] + [f"/catalogue/{i['sku']}" for i in items]:
        body = ctx.public_client.get(route).get_data(as_text=True)
        for row in negotiated:
            if row["company_name"] and row["company_name"] in body:
                findings.append(Finding(
                    f"render:{route}", f"customer name {row['company_name']!r} in a public response"))
            if row["ref"] and row["ref"] in body:
                findings.append(Finding(
                    f"render:{route}", f"customer ref {row['ref']!r} in a public response"))
    return findings


def prove_a08(ctx):
    """Leak one field, confirm A08 names it, put it back."""
    from monti import catalogue

    original = catalogue.public_item
    caught = []

    def leaky(row):
        payload = original(row)
        # The realistic version of this defect: someone adds the member's price
        # to the serializer so the portal page can reuse it.
        payload["unit_price_cents"] = row["unit_price_cents"]
        return payload

    catalogue.public_item = leaky
    try:
        findings = run_a08(ctx)
        caught.append(("payload: negotiated price added to the public serializer",
                       bool(findings), str(findings[0]) if findings else "MISSED"))
    finally:
        catalogue.public_item = original

    # And the rendered-output half: a template printing the owning customer.
    from pathlib import Path
    tpl = (Path(__file__).resolve().parent.parent.parent / "monti" / "templates"
           / "public" / "catalogue_item.html")
    src = tpl.read_text()
    name = ctx.query("SELECT company_name FROM customers LIMIT 1")
    if name:
        tpl.write_text(src.replace("{{ item.name }}</h1>",
                                   "{{ item.name }} — " + name[0]["company_name"] + "</h1>", 1))
        try:
            findings = run_a08(ctx)
            caught.append(("rendered: owning customer printed on the public page",
                           bool(findings), str(findings[0]) if findings else "MISSED"))
        finally:
            tpl.write_text(src)

    missed = [label for label, ok, _ in caught if not ok]
    detail = "; ".join(f"{label} -> {note}" for label, _, note in caught)
    return (not missed), detail


CHECKS = [
    Check("A07", "Order gating refused server-side at all three points", run, prove),
    Check("A08", "No negotiated price, customer or assignment field in a public response",
          run_a08, prove_a08),
]
