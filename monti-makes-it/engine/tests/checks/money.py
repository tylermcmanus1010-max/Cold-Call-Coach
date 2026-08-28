"""A11 — the 24-hour manufacturer review gate (§9.7).

The hard constraint: every paid order sits in review before anything is
produced, and shipping an order whose review has not cleared is a P0. §9.7 says
it is enforced in code, which means the check has to call the function directly
as well as try the route — a guard that only exists in a view is one internal
caller away from being bypassed.
"""
from . import Check, Finding


def run(ctx):
    findings = []
    order_id = ctx.make_paid_unreviewed_order()
    try:
        # By direct call.
        with ctx.app.app_context():
            from monti import orders as orders_mod
            try:
                orders_mod.ship_order(order_id, actor="A11", carrier="Test", tracking="X1")
                findings.append(Finding(
                    "orders.ship_order",
                    f"shipped order {order_id} with no cleared review and did not raise"))
            except ValueError:
                pass

        # And by route, as an admin — the same guard has to hold there.
        r = ctx.admin_client.post(f"/admin/orders/{order_id}/ship",
                                  data={"carrier": "Test", "tracking": "X1",
                                        "_csrf": ctx.csrf(ctx.admin_client)},
                                  follow_redirects=True)
        row = ctx.query("SELECT status, shipped_at FROM orders WHERE id = ?", (order_id,))
        if row and row[0]["shipped_at"]:
            findings.append(Finding(
                "admin.ship_order",
                f"the route shipped order {order_id} before its review cleared "
                f"(HTTP {r.status_code})"))
    finally:
        ctx.execute("DELETE FROM order_events WHERE order_id = ?", (order_id,))
        ctx.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        ctx.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    return findings


def prove(ctx):
    """Remove the guard, confirm A11 names it, put it back."""
    from pathlib import Path
    orders = Path(__file__).resolve().parent.parent.parent / "monti" / "orders.py"
    original = orders.read_text()
    # The whole statement, not just its first line: the raise spans three lines
    # and neutralising only the first leaves a dangling continuation that fails
    # to parse, which reports as "the proof crashed" rather than as a result.
    guard = '''    if not state["can_ship"]:
        raise ValueError(
            "This order has not cleared the manufacturer review window — it cannot ship yet."
        )
'''
    if guard not in original:
        return False, "ship_order's guard is not where the proof expects it"
    try:
        orders.write_text(original.replace(
            guard, '''    if not state["can_ship"]:
        pass
''', 1))
        ctx.reload()
        findings = run(ctx)
        caught = bool(findings)
        note = str(findings[0]) if findings else "MISSED"
    finally:
        orders.write_text(original)
        ctx.reload()
    return caught, f"ship_order's review guard removed -> {note}"


CHECKS = [Check("A11", "An order cannot ship before its manufacturer review clears",
                run, prove)]
