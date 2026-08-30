"""A39 — the merged product list, and the tenancy rule the merge could break.

My catalog and My products were two tabs for one object at two ages. Merging
them means joining two lists that were scoped by DIFFERENT rules:

  decision_items  scoped by `customer_id = ?`, in SQL.
  catalog_items   scoped by registrations and tags, through
                  `catalog.items_for_customer`.

`decision_items.catalog_item_id` sits between them, and following it is one line
shorter than reading the visible set. It is also how a merge like this leaks: if
a member's product points at a catalogue line that is NOT registered to them —
a registration deactivated, an admin mistake, a line reassigned — the shortcut
puts another account's product name, price, MOQ and lead time on this member's
screen, and it looks completely normal.

So this check has three parts.

  Isolation.   Point a member's item at a catalogue line that belongs to someone
               else, then assert nothing from that line reaches the merged list
               or the rendered page. §1.8 says isolation lives in the data layer,
               so the assertion is on what `products.for_member` returns as well
               as on the HTML — a view that happens not to print a leaked value
               is still holding it.

  Completeness. The merge must not lose anything. Every decision item the member
               has, and every catalogue line they can see, appears exactly once.
               A merge that drops the orphan catalogue lines would look tidy and
               would have hidden Boars Head's 1000ml container, which is
               registered to them without ever having come through the door.

  Price.       No client-facing price without provenance (§11.1), and no price
               described as something it is not. The tab this replaced read
               three keys `items_for_customer` does not return, so every card
               rendered "$0.00" under a badge asserting it was that member's
               negotiated price — on matrix-priced items where no single figure
               is the answer at all. A row that reports a price must have an
               input id or a registration behind it, and a row with no price
               must say so rather than showing zero.
"""
from . import Check, Finding

PROBE_SKU = "MMI-A39-OTHER"


def _other_customers_item(ctx):
    """A catalogue line belonging to the OTHER member, registered only to them."""
    rows = ctx.query("SELECT id FROM catalog_items WHERE sku = ?", (PROBE_SKU,))
    if rows:
        item_id = rows[0]["id"]
    else:
        item_id = ctx.execute(
            "INSERT INTO catalog_items (sku, name, description, specs, materials, "
            "unit_price_cents, moq, lead_time_days, tags, is_active) "
            "VALUES (?, 'A39 probe — other account only', 'A39-DESCRIPTION-LEAK', "
            "'A39-SPEC-LEAK', 'A39-MATERIAL-LEAK', 4242, 7777, 99, NULL, 1)",
            (PROBE_SKU,))
    if not ctx.query("SELECT id FROM catalogue_registrations WHERE item_id = ? "
                     "AND customer_id = ?", (item_id, ctx.other_customer_id)):
        ctx.execute(
            "INSERT INTO catalogue_registrations (item_id, customer_id, unit_price_cents, "
            "moq, active, assigned_by) VALUES (?, ?, 4242, 7777, 1, 'a39-probe')",
            (item_id, ctx.other_customer_id))
    return item_id


def run(ctx):
    from monti import products as products_mod

    findings = []
    with ctx.app.app_context():
        customer = ctx.query("SELECT * FROM customers WHERE id = ?",
                             (ctx.member_customer_id,))[0]

        # ---- completeness, before anything is perturbed -------------------
        rows = products_mod.for_member(customer)
        by_ref = {r["ref"] for r in rows}
        if len(by_ref) != len(rows):
            findings.append(Finding("products.for_member",
                                    "the same product appears twice in one list"))

        items = ctx.query("SELECT * FROM decision_items WHERE customer_id = ?",
                          (ctx.member_customer_id,))
        for item in items:
            if item["ref"] not in by_ref:
                findings.append(Finding(
                    f"decision_items.{item['ref']}",
                    "a product the member asked for is missing from the merged list — "
                    "the merge lost it"))

        from monti import catalog as catalog_mod
        visible = catalog_mod.items_for_customer(customer)
        linked = {i["catalog_item_id"] for i in items if i["catalog_item_id"]}
        for entry in visible:
            reachable = entry["id"] in linked or entry["sku"] in by_ref
            if not reachable:
                findings.append(Finding(
                    f"catalog_items.{entry['sku']}",
                    "a catalogue line this member can order is not reachable from the "
                    "merged list — before the merge it was on the other tab, and now "
                    "it is nowhere"))

        # ---- price: no number without provenance, no zero standing in ----
        for row in rows:
            if row["price_cents"] is None:
                continue
            if row["price_basis"] is None:
                findings.append(Finding(
                    f"{row['ref']}",
                    f"shows {row['price_cents']} with no basis — a number the page "
                    "cannot say the meaning of"))
            if row["price_basis"] == "matrix" and not row["price_input_id"]:
                findings.append(Finding(
                    f"{row['ref']}",
                    "a matrix price with no input id behind it — §11.1 wants the "
                    "provenance carried with the figure, not asserted separately"))
            if row["price_cents"] == 0:
                findings.append(Finding(
                    f"{row['ref']}",
                    "renders a price of zero. The tab this replaced did that on every "
                    "card, under a badge calling it the member's negotiated price"))
            if row["price_basis"] == "negotiated":
                reg = ctx.query(
                    "SELECT unit_price_cents FROM catalogue_registrations WHERE item_id = ? "
                    "AND customer_id = ? AND active = 1",
                    (row["item_id"], ctx.member_customer_id))
                if not reg or reg[0]["unit_price_cents"] is None:
                    findings.append(Finding(
                        f"{row['ref']}",
                        "calls a price negotiated with no negotiated price on the "
                        "registration"))

        # ---- isolation ----------------------------------------------------
        foreign_id = _other_customers_item(ctx)
        target = items[0] if items else None
        if target is None:
            findings.append(Finding("harness",
                                    "the member has no product to point at a foreign line"))
            return findings
        original = target["catalog_item_id"]
        ctx.execute("UPDATE decision_items SET catalog_item_id = ? WHERE id = ?",
                    (foreign_id, target["id"]))
        try:
            leaked = products_mod.for_member(customer)
            for row in leaked:
                entry = row["entry"]
                if entry is not None and entry["id"] == foreign_id:
                    findings.append(Finding(
                        f"products.for_member → {row['ref']}",
                        "carries a catalogue line registered to another account, "
                        "reached by following catalog_item_id instead of reading the "
                        "visible set"))
                if row["sku"] == PROBE_SKU or (row["name"] or "").startswith("A39 probe"):
                    findings.append(Finding(
                        f"products.for_member → {row['ref']}",
                        "shows another account's product name"))
                if row["price_cents"] == 4242 or row["moq"] == 7777:
                    findings.append(Finding(
                        f"products.for_member → {row['ref']}",
                        "shows another account's negotiated price or MOQ"))

            # And on the rendered page, because a value held and not printed is
            # still held: the next template change prints it.
            page = ctx.member_client.get("/portal/products", follow_redirects=True)
            body = page.data
            for marker in (b"A39-DESCRIPTION-LEAK", b"A39-SPEC-LEAK", b"A39-MATERIAL-LEAK",
                           PROBE_SKU.encode(), b"7,777", b"$42.42"):
                if marker in body:
                    findings.append(Finding(
                        "GET /portal/products",
                        f"rendered {marker.decode()} — another account's data on this "
                        "member's screen"))

            # The mismatch must be reported rather than silently absorbed.
            if not products_mod.unlinked(customer):
                findings.append(Finding(
                    "products.unlinked",
                    "a product points at a catalogue line this member cannot see and "
                    "nothing reports it — the list drops it correctly and says nothing, "
                    "so the underlying defect stays invisible"))
        finally:
            ctx.execute("UPDATE decision_items SET catalog_item_id = ? WHERE id = ?",
                        (original, target["id"]))
    return findings


def prove(ctx):
    """Three defects: the shortcut join, a dropped orphan, and the zero price."""
    from pathlib import Path

    caught = []
    source = Path(__file__).resolve().parents[2] / "monti" / "products.py"

    def attempt(label, before, after, matches):
        original = source.read_text()
        broken = original.replace(before, after, 1)
        assert broken != original, f"proof {label!r} no longer matches the source"
        source.write_text(broken)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            source.write_text(original)
            ctx.reload()

    # 1. the shortcut: follow catalog_item_id instead of reading the visible set.
    attempt("the merge followed catalog_item_id instead of the visible set",
            '        entry = visible.get(item["catalog_item_id"]) if item["catalog_item_id"] else None',
            '        entry = None\n'
            '        if item["catalog_item_id"]:\n'
            '            from .db import query as _q\n'
            '            _r = _q("SELECT * FROM catalog_items WHERE id = ?",\n'
            '                    (item["catalog_item_id"],), one=True)\n'
            '            if _r is not None:\n'
            '                entry = {"id": _r["id"], "sku": _r["sku"], "name": _r["name"],\n'
            '                         "description": _r["description"], "specs": _r["specs"],\n'
            '                         "materials": _r["materials"], "category": _r["category"],\n'
            '                         "moq": _r["moq"], "lead_time_days": _r["lead_time_days"],\n'
            '                         "list_price_cents": _r["unit_price_cents"]}',
            lambda f: "another account" in f.detail)

    # 2. the tidy merge: drop catalogue lines with no product behind them.
    attempt("catalogue lines with no product behind them were dropped",
            '''    for entry in visible.values():
        if entry["id"] not in claimed:
            rows.append(_row(customer, item=None, entry=entry))''',
            '''    for entry in visible.values():
        if False:
            rows.append(_row(customer, item=None, entry=entry))''',
            lambda f: "is nowhere" in f.detail)

    # 3. the old bug, put back: a missing price becomes zero.
    attempt("a missing price rendered as zero",
            "    return None, None, None\n\n\ndef for_member",
            "    return 0, None, \"negotiated\"\n\n\ndef for_member",
            lambda f: "price of zero" in f.detail or "no negotiated price" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A39", "The merged product list keeps both tenancy rules and both lists",
                run, prove)]
