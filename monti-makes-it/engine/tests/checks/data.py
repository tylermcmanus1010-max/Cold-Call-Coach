"""A14 — no fixture row survives (§0.3.5).

"Halcyon Goods returns zero rows" is the stated acceptance criterion, but a
check that looks for one company name passes the moment somebody seeds a
different one. This asserts the general property — zero rows carrying the
fixture stamp, in any swept table — and then also asserts the specific names the
protocol calls out, because those are the ones a reader will look for.

Orphans count as survivors. A row whose parent is gone is data the purge was
supposed to take.
"""
from . import Check, Finding

# Named in §0.3.5 and Appendix B, plus the demo logins START-HERE documents.
NAMED_FIXTURES = ["Halcyon Goods", "Northfield Outfitters", "Verano Skincare",
                  "Grit & Grain Coffee", "Solace Home"]


def run(ctx):
    from monti.db import FIXTURE_TABLES

    findings = []
    for table in FIXTURE_TABLES:
        rows = ctx.query(f"SELECT COUNT(*) AS c FROM {table} WHERE is_fixture = 1")
        if rows[0]["c"]:
            findings.append(Finding(table, f"{rows[0]['c']} fixture row(s) survived the purge"))

    for name in NAMED_FIXTURES:
        rows = ctx.query("SELECT COUNT(*) AS c FROM customers WHERE company_name = ?", (name,))
        if rows[0]["c"]:
            findings.append(Finding("customers", f"seeded customer {name!r} is still present"))

    with ctx.app.app_context():
        from monti import purge
        for orphan in purge.orphans():
            findings.append(Finding(
                f"{orphan['table']}.{orphan['column']}",
                f"{orphan['count']} row(s) point at a {orphan['parent']} row that is gone"))

    # A customer with no agent is the same class of leftover: the contract says
    # no customer exists without one.
    with ctx.app.app_context():
        from monti import agents
        for row in agents.unprovisioned_customers():
            findings.append(Finding(
                "client_agents", f"customer {row['company_name']!r} has no client agent"))
    return findings


def prove(ctx):
    """Reinsert one fixture customer and one orphan, confirm A14 names both."""
    caught = []

    cid = ctx.execute(
        "INSERT INTO customers (ref, company_name, email, is_fixture) "
        "VALUES ('MMI-C-9999', 'Halcyon Goods', 'proof@example.com', 1)")
    try:
        findings = run(ctx)
        hit = [f for f in findings if "Halcyon" in f.detail or "fixture row" in f.detail]
        caught.append(("a seeded customer put back", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ctx.execute("DELETE FROM customers WHERE id = ?", (cid,))

    # An orphan: an order_items row whose order does not exist. It has to be
    # written on a connection with foreign keys off, which is exactly how a real
    # orphan arrives — the pragma is per-connection, so any code path that opens
    # a connection and forgets it can write one, and that is the row the purge's
    # sweep exists to find.
    conn = ctx.raw_sqlite()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cur = conn.execute(
            "INSERT INTO order_items (order_id, name, unit_price_cents, quantity, "
            "line_total_cents) VALUES (999999, 'proof line', 1, 1, 1)")
        oid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    try:
        findings = run(ctx)
        hit = [f for f in findings if "order_items" in f.where]
        caught.append(("an orphan line with no order", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ctx.execute("DELETE FROM order_items WHERE id = ?", (oid,))

    missed = [label for label, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{l} -> {n}" for l, _, n in caught)


CHECKS = [Check("A14", "Zero fixture rows, zero orphans, every customer has an agent",
                run, prove)]
