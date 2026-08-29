"""A37 — one door. A request and the product it becomes are one act.

There were two doors, and they wrote different things. The public quote form
created a `quotes` row — a reference, a 24-hour clock, a quota debit — and no
product. "Describe it badly" in the portal created a `decision_items` row — a
product with a stage tracker — and no quote, so no clock and no debit. Nothing
connected them, and the two counters over the same allowance each saw half the
traffic: `membership.quota_state` counts rows in `quotes`, `genome.capacity`
sums weights in `capacity_ledger`, and neither could see what the other door
made.

`monti/intake.py` is now the only path that writes a request, and this check is
what keeps it that way. It has three parts:

  The probe.     Post a real submission through the portal door and assert all
                 three records exist and are linked to each other. Behaviour,
                 not structure — a helper that exists but is not called would
                 pass a structural check and fail this one.

  The invariant. No `quotes` row anywhere without a product behind it. This
                 direction is safe to assert globally because nothing but
                 `create_request` writes that table.

  The accounting. The weighted debit for the probe must be visible to
                 `genome.capacity` and the request itself to
                 `membership.quota_state`. Half a record is exactly what used to
                 slip past one of the two counters, so both are asked.

The asymmetry in the second part is deliberate and is explained where the rule
lives (`monti.intake.orphans`): a product with no quote is only a defect when it
came through the door, and Boars Head's two migrated items did not.
"""
from . import Check, Finding


class _Raised:
    """Stands in for a response when the door raised instead of answering."""

    status_code = 500
    headers = {}

    def __init__(self, exc):
        self.exc = exc

    def __str__(self):
        return f"{type(self.exc).__name__}: {self.exc}"


def _probe(ctx):
    """Send one request through the portal door. Returns the created rows."""
    body = {
        "summary": "A37 probe — lidded tray for a hot counter",
        "quantity": "a few hundred thousand a year",
        "material": "board of some kind",
        "needed_by": "before the summer menu",
        "brought": "A37 probe — four phone photos with a ruler in frame",
        "weight": "4",
        "_csrf": ctx.csrf(ctx.member_client),
    }
    # A door that raises is a defect this check should name rather than a crash
    # that takes the suite down with it: half a request written and then an
    # exception is the worst version of the split, because the member sees an
    # error page and the database keeps the fragment.
    try:
        response = ctx.member_client.post("/portal/requests", data=body,
                                          follow_redirects=False)
    except Exception as exc:                                    # noqa: BLE001
        response = _Raised(exc)
    quote = ctx.query(
        "SELECT * FROM quotes WHERE title = ? ORDER BY id DESC LIMIT 1",
        (body["summary"],))
    item = ctx.query(
        "SELECT * FROM decision_items WHERE quote_id = ? ORDER BY id DESC LIMIT 1",
        (quote[0]["id"],)) if quote else []
    return response, (quote[0] if quote else None), (item[0] if item else None)


def run(ctx):
    from monti import genome, intake, membership

    findings = []
    with ctx.app.app_context():
        customer = ctx.query("SELECT * FROM customers WHERE id = ?",
                             (ctx.member_customer_id,))[0]
        before_capacity = genome.capacity(customer)["used"]
        before_quota = membership.quota_state(customer)["used"]

        response, quote, item = _probe(ctx)

        if isinstance(response, _Raised):
            findings.append(Finding(
                "POST /portal/requests",
                f"the door raised instead of answering — {response}"))
        elif response.status_code not in (301, 302):
            findings.append(Finding(
                "POST /portal/requests",
                f"a submission returned {response.status_code} instead of redirecting "
                f"to the product it created"))
        if quote is None:
            findings.append(Finding(
                "POST /portal/requests",
                "wrote no quote — the request has no reference and no 24-hour clock"))
        if item is None:
            findings.append(Finding(
                "POST /portal/requests",
                "wrote no product linked to the quote — the member has a reference "
                "with nothing behind it"))

        if quote is not None and item is not None:
            # The redirect has to land on the product. A submission that creates
            # a product and then sends the member somewhere else is the split
            # this check exists to prevent, in the smallest possible form.
            location = response.headers.get("Location") or ""
            if not isinstance(response, _Raised) and \
                    f"/portal/products/{item['ref']}" not in location:
                findings.append(Finding(
                    "POST /portal/requests",
                    f"redirected to {location!r} rather than to "
                    f"the product {item['ref']} it just created"))

            ledger_rows = ctx.query(
                "SELECT * FROM capacity_ledger WHERE item_id = ?", (item["id"],))
            if not ledger_rows:
                findings.append(Finding(
                    f"{quote['ref']} / {item['ref']}",
                    "no capacity row — the request was never debited"))
            elif ledger_rows[0]["quote_id"] != quote["id"]:
                findings.append(Finding(
                    f"{quote['ref']} / {item['ref']}",
                    "the capacity row does not carry the quote id, so the debit "
                    "cannot be traced back to the request that caused it"))
            elif ledger_rows[0]["charged"] != 4:
                findings.append(Finding(
                    f"{quote['ref']} / {item['ref']}",
                    f"charged {ledger_rows[0]['charged']} units for a request the "
                    f"member was shown as costing 4"))

            # Both counters must see it. One of them seeing it is the old bug.
            after = ctx.query("SELECT * FROM customers WHERE id = ?", (customer["id"],))[0]
            if genome.capacity(after)["used"] <= before_capacity:
                findings.append(Finding(
                    "genome.capacity", "the weighted allowance did not move for a "
                    "request that was charged"))
            if membership.quota_state(after)["used"] <= before_quota:
                findings.append(Finding(
                    "membership.quota_state", "the request counter did not move — this "
                    "door is invisible to the gate that limits requests"))

        # The global invariant, and the door-failure half of the other direction.
        orphans = intake.orphans()
        for row in orphans["quotes_without_item"]:
            findings.append(Finding(
                f"quotes.{row['ref']}",
                "a request with no product behind it — half a record"))
        for row in orphans["items_without_quote"]:
            findings.append(Finding(
                f"decision_items.{row['ref']}",
                "a product with a capacity debit but no request behind it, so it was "
                "charged for something that has no clock and no reference"))

        # Clean up, by what the probe wrote rather than by what it managed to
        # link. A proof that breaks the link would otherwise leave the unlinked
        # half behind for the next proof to trip over — which is the check
        # reporting its own litter as a defect.
        probe = "A37 probe"
        for row in ctx.query(
                "SELECT id FROM decision_items WHERE source LIKE ? OR quote_id IN "
                "(SELECT id FROM quotes WHERE title LIKE ?) OR id IN "
                "(SELECT item_id FROM capacity_ledger WHERE label LIKE ?)",
                (f"%{probe}%", f"%{probe}%", f"%{probe}%")):
            ctx.execute("DELETE FROM capacity_ledger WHERE item_id = ?", (row["id"],))
            ctx.execute("DELETE FROM decision_items WHERE id = ?", (row["id"],))
        for row in ctx.query("SELECT id, ref FROM quotes WHERE title LIKE ?",
                             (f"%{probe}%",)):
            ctx.execute("DELETE FROM capacity_ledger WHERE quote_id = ?", (row["id"],))
            ctx.execute("DELETE FROM calendar_events WHERE title LIKE ?",
                        (f"%{row['ref']}%",))
            ctx.execute("DELETE FROM crm_activities WHERE body LIKE ?", (f"%{row['ref']}%",))
            ctx.execute("DELETE FROM quotes WHERE id = ?", (row["id"],))
    return findings


def prove(ctx):
    """Take the product away, then take the link away, then leave a quote orphaned."""
    from pathlib import Path

    caught = []
    source = Path(__file__).resolve().parents[2] / "monti" / "intake.py"
    original = source.read_text()

    # 1. the door writes a quote and no product — the public form's old shape
    broken = original.replace(
        '    count = query("SELECT COUNT(*) AS c FROM decision_items", one=True)["c"]',
        '    return (query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True), None)\n'
        '    count = query("SELECT COUNT(*) AS c FROM decision_items", one=True)["c"]', 1)
    assert broken != original
    source.write_text(broken)
    try:
        ctx.reload()
        findings = run(ctx)
        hit = [f for f in findings if "no product" in f.detail or "the door raised" in f.detail]
        caught.append(("the door wrote a quote with no product", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        source.write_text(original)
        ctx.reload()

    # 2. the two records exist but nothing links them
    broken = original.replace('"VALUES (?, ?, ?, ?, \'PENDING\', 1, ?, ?, 0)",\n'
                              '        (d_ref, f"Unapproved item {count + 1:03d}", customer["id"], quote_id,',
                              '"VALUES (?, ?, ?, ?, \'PENDING\', 1, ?, ?, 0)",\n'
                              '        (d_ref, f"Unapproved item {count + 1:03d}", customer["id"], None,', 1)
    assert broken != original
    source.write_text(broken)
    try:
        ctx.reload()
        findings = run(ctx)
        hit = [f for f in findings if "half a record" in f.detail
               or "no product linked" in f.detail]
        caught.append(("the product was created without the link back to the request",
                       bool(hit), str(hit[0]) if hit else "MISSED"))
    finally:
        source.write_text(original)
        ctx.reload()

    # 3. the capacity debit loses the quote id — the debit stops being traceable
    broken = original.replace(
        '        (customer["id"], quote_id, item_id, title[:120], classify(weight), weight, weight))',
        '        (customer["id"], None, item_id, title[:120], classify(weight), weight, weight))', 1)
    assert broken != original
    source.write_text(broken)
    try:
        ctx.reload()
        findings = run(ctx)
        hit = [f for f in findings if "does not carry the quote id" in f.detail]
        caught.append(("the capacity debit lost the request it was charged for",
                       bool(hit), str(hit[0]) if hit else "MISSED"))
    finally:
        source.write_text(original)
        ctx.reload()

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A37", "Every request writes one quote, one product and one debit, linked",
                run, prove)]
