"""A15 — number provenance (§11.1).

Every price, lead time, MOQ, freight figure and curve point a client sees
resolves to a stored admin input with a publish timestamp. A rendered field with
no input id behind it is a P1.

The check has three halves, and the second and third are the ones that catch
real defects.

  The payload.   Walk every figure the Decision Room can render and assert each
                 carries input ids. Cheap, and catches an arithmetic path that
                 forgot to pass provenance along.

  The gate.      An entered-but-unpublished input must be invisible. This is the
                 half that catches the failure nobody notices: a price that is
                 correct, traceable, and was never released.

  Extrapolation. §11.1 permits interpolation along an entered curve and forbids
                 extrapolation past it. So the check asks for a quantity outside
                 the entered band and asserts the surface clamps rather than
                 quoting — a price at a quantity nobody entered is invented, and
                 it looks exactly like a real one.
"""
import re

from . import Check, Finding


def _entered_ceiling(ctx, item):
    """The largest quantity an admin actually priced, straight from the rows.

    Deliberately does not call into `monti.decisionroom` — see the note at the
    extrapolation assertion.
    """
    if item["qty_max"]:
        return item["qty_max"]
    if item["catalog_item_id"]:
        row = ctx.query(
            "SELECT MAX(COALESCE(c.quantity_max, c.quantity_min)) AS hi "
            "FROM price_matrix_cells c JOIN price_matrices m ON m.id = c.matrix_id "
            "WHERE m.item_id = ? AND m.published_at IS NOT NULL", (item["catalog_item_id"],))
        return row[0]["hi"] if row and row[0]["hi"] else None
    return None


def run(ctx):
    from monti import decisionroom as dr

    findings = []
    with ctx.app.app_context():
        items = ctx.query("SELECT * FROM decision_items WHERE published_at IS NOT NULL")
        if not items:
            return [Finding("A15", "no published Decision Room item exists — an "
                                   "unexercised provenance check is not a pass")]

        for item in items:
            # --- the payload -------------------------------------------------
            record = dr.provenance(item["id"])
            if not record["fields"]:
                findings.append(Finding(
                    f"item {item['ref']}",
                    "published, but renders no figure with provenance attached"))
            # The material input is read into every ex-works figure, so its id
            # has to appear in every figure derived from one. Asserting merely
            # "at least one input id" is too weak: a figure built from four
            # inputs that reports one still passes, and the trail it lost is
            # exactly the part a dispute would need.
            material = ctx.query(
                "SELECT id FROM pricing_inputs WHERE item_id = ? AND field = 'material_unit' "
                "AND published_at IS NOT NULL ORDER BY id DESC LIMIT 1", (item["id"],))
            material_id = material[0]["id"] if material else None

            for field in record["fields"]:
                if not field.get("input_ids"):
                    findings.append(Finding(
                        f"{item['ref']} · {field['field']}",
                        "rendered with no admin input behind it"))
                elif material_id and material_id not in field["input_ids"]:
                    findings.append(Finding(
                        f"{item['ref']} · {field['field']}",
                        f"does not carry the material input ({material_id}) it was "
                        f"computed from — part of the trail was dropped"))

            # --- every input that backs it is published ----------------------
            for input_id in {i for f in record["fields"] for i in f.get("input_ids", [])}:
                row = ctx.query("SELECT * FROM pricing_inputs WHERE id = ?", (input_id,))
                if not row:
                    findings.append(Finding(
                        f"{item['ref']}", f"references input {input_id}, which does not exist"))
                elif not row[0]["published_at"]:
                    findings.append(Finding(
                        f"{item['ref']} · input {input_id}",
                        "an unpublished input is behind a rendered figure"))
                elif not row[0]["entered_by"]:
                    findings.append(Finding(
                        f"{item['ref']} · input {input_id}", "no admin is recorded against it"))

            # --- the gate ----------------------------------------------------
            published = dr.cost_inputs(item["id"], published_only=True)
            everything = dr.cost_inputs(item["id"], published_only=False)
            for field, entry in everything.items():
                if entry["published_at"] is None and published.get(field, {}).get(
                        "input_id") == entry["input_id"]:
                    findings.append(Finding(
                        f"{item['ref']} · {field}",
                        "an unpublished input is being served to members"))

            # --- no extrapolation --------------------------------------------
            #
            # The ceiling is read from the stored data, not from
            # `dr.quantity_bounds()`. Asking the implementation what its own
            # limit is and then checking it respects that limit is circular:
            # widen the function and the check widens with it, which is how this
            # assertion passed against a deliberately broken band on its first
            # run. §11.1's rule is about the quantities an admin actually
            # entered, so that is what this reads.
            entered_max = _entered_ceiling(ctx, item)
            if entered_max:
                body = ctx.member_client.get(
                    f"/portal/room/{item['ref']}?qty={entered_max * 10}"
                ).get_data(as_text=True)
                shown = re.search(r'id="qtyRead">([\d,]+)<', body)
                if shown is None:
                    findings.append(Finding(
                        f"{item['ref']}",
                        "the room did not render a quantity for a published item"))
                elif int(shown.group(1).replace(",", "")) > entered_max:
                    findings.append(Finding(
                        f"{item['ref']}",
                        f"quoted at {shown.group(1)} units, past the {entered_max:,} "
                        f"an admin actually entered — that price was extrapolated"))
            else:
                # No band means no priceable quantity, so the room must not be
                # showing a price at all.
                if 'class="card strat' in ctx.member_client.get(
                        f"/portal/room/{item['ref']}").get_data(as_text=True):
                    findings.append(Finding(
                        f"{item['ref']}",
                        "renders strategy cards with no entered quantity band behind them"))
    return findings


def prove(ctx):
    """Null an input id, unpublish an input, and widen the band past what was priced."""
    from monti import decisionroom as dr

    caught = []
    with ctx.app.app_context():
        item = ctx.query(
            "SELECT * FROM decision_items WHERE published_at IS NOT NULL LIMIT 1")
    if not item:
        return False, "no published item to break"
    item = item[0]

    # 1. a figure whose provenance was dropped on the way through the arithmetic
    original_ex = dr.ex_works

    def forgetful(costs, quantity, **kw):
        cents, _used = original_ex(costs, quantity, **kw)
        return cents, []                     # the number survives, the trail does not

    dr.ex_works = forgetful
    try:
        findings = run(ctx)
        # Matches either wording: a figure with no input at all, or one that
        # kept an input but lost the material id it was computed from. The
        # second is what this defect actually produces, and filtering only for
        # the first reported MISSED while the check was firing correctly.
        hit = [f for f in findings
               if "no admin input behind it" in f.detail
               or "part of the trail was dropped" in f.detail]
        caught.append(("provenance dropped from the arithmetic", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        dr.ex_works = original_ex

    # 2. an input serving members without ever having been published
    row = ctx.query(
        "SELECT * FROM pricing_inputs WHERE item_id = ? AND published_at IS NOT NULL LIMIT 1",
        (item["id"],))
    if row:
        row = row[0]
        stamp, by = row["published_at"], row["published_by"]
        ctx.execute("UPDATE pricing_inputs SET published_at = NULL WHERE id = ?", (row["id"],))
        try:
            findings = run(ctx)
            hit = [f for f in findings if "unpublished" in f.detail
                   or "no admin input behind it" in f.detail]
            caught.append(("an input unpublished under a live price", bool(hit),
                           str(hit[0]) if hit else "MISSED"))
        finally:
            ctx.execute(
                "UPDATE pricing_inputs SET published_at = ?, published_by = ? WHERE id = ?",
                (stamp, by, row["id"]))

    # 3. the band widened past what was actually priced — the extrapolation case
    with ctx.app.app_context():
        bounds = dr.quantity_bounds(item)
    if bounds:
        saved_min, saved_max = item["qty_min"], item["qty_max"]
        original_bounds = dr.quantity_bounds

        def unbounded(_item):
            band = original_bounds(_item)
            if band:
                band = {**band, "max": band["max"] * 100}
            return band

        dr.quantity_bounds = unbounded
        try:
            findings = run(ctx)
            hit = [f for f in findings if "extrapolated" in f.detail]
            caught.append(("the quantity band widened past the entered curve", bool(hit),
                           str(hit[0]) if hit else "MISSED"))
        finally:
            dr.quantity_bounds = original_bounds
            ctx.execute("UPDATE decision_items SET qty_min = ?, qty_max = ? WHERE id = ?",
                        (saved_min, saved_max, item["id"]))

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A15", "Every rendered Decision Room figure traces to a published input",
                run, prove)]
