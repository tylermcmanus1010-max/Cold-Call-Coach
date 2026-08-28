"""Deleting the demo data, and being able to prove it (§0.3.5, WI-X-01…03).

The order is not negotiable: inventory, then backup, then delete, then sweep for
orphans, then verify. A purge that runs before a restorable backup exists is a
one-way door, and the thing being deleted is a database.

Orphans are the part that gets missed. Deleting a customer takes their quotes
and orders with it through ON DELETE CASCADE, but a `catalogue_registrations`
row pointing at a deleted item, or an `order_items` row whose order is gone,
survives happily in SQLite unless foreign keys are actually enforced — and they
are per-connection. So the sweep looks for orphans explicitly rather than
trusting the pragma, and A14 asserts it found none.
"""
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app

from .db import FIXTURE_TABLES, execute, get_db, query

# Dependent tables and the parent each one points at. Checked after the delete;
# a row here whose parent is gone is a purge that did not finish.
ORPHAN_CHECKS = [
    ("quotes", "customer_id", "customers"),
    ("orders", "customer_id", "customers"),
    ("order_items", "order_id", "orders"),
    ("order_events", "order_id", "orders"),
    ("quote_files", "quote_id", "quotes"),
    ("estimates", "quote_id", "quotes"),
    ("crm_activities", "customer_id", "customers"),
    ("cart_items", "customer_id", "customers"),
    ("catalogue_registrations", "customer_id", "customers"),
    ("catalogue_registrations", "item_id", "catalog_items"),
    ("item_images", "item_id", "catalog_items"),
    ("item_genome", "item_id", "catalog_items"),
    ("tools", "customer_id", "customers"),
    ("client_agents", "customer_id", "customers"),
    ("agent_proposals", "customer_id", "customers"),
    ("price_matrices", "customer_id", "customers"),
    ("price_matrix_cells", "matrix_id", "price_matrices"),
    ("security_log", "customer_id", "customers"),
    ("ledger_entries", "customer_id", "customers"),
    ("ledger_entries", "reverses_id", "ledger_entries"),
    ("users", "customer_id", "customers"),
]


def inventory():
    """Every fixture row, per table, with the evidence that it is fixture data."""
    rows = []
    for table in FIXTURE_TABLES:
        label = "company_name" if table in ("customers", "applications") else (
            "sku" if table == "catalog_items" else
            "receipt_no" if table == "ledger_entries" else "ref")
        for r in query(f"SELECT id, {label} AS label FROM {table} WHERE is_fixture = 1"):
            rows.append({
                "table": table,
                "id": r["id"],
                "label": r["label"],
                "evidence": "is_fixture = 1, stamped by monti.seed at insert time",
            })
    return rows


def backup(reason="pre-purge"):
    """Copy the database file, and verify the copy opens and counts the same.

    A backup nobody has opened is a file, not a backup. This one is read back
    and its customer count compared before the caller is allowed to proceed.
    """
    src = Path(current_app.config["DATABASE_PATH"])
    if not src.exists():
        raise FileNotFoundError(f"no database at {src}")

    # WAL mode keeps recent writes outside the main file, so a plain copy can
    # miss them. Checkpoint first.
    get_db().execute("PRAGMA wal_checkpoint(TRUNCATE)")

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dest = src.parent / "backups" / f"{src.stem}-{reason}-{stamp}.db"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    before = query("SELECT COUNT(*) AS c FROM customers", one=True)["c"]
    conn = sqlite3.connect(dest)
    try:
        restored = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    if integrity != "ok":
        raise RuntimeError(f"backup at {dest} failed integrity_check: {integrity}")
    if restored != before:
        raise RuntimeError(
            f"backup at {dest} has {restored} customers, live database has {before}")
    return {"path": str(dest), "customers": restored, "integrity": integrity}


def orphans():
    """Dependent rows whose parent no longer exists."""
    found = []
    for table, column, parent in ORPHAN_CHECKS:
        rows = query(
            f"SELECT COUNT(*) AS c FROM {table} t "
            f"WHERE t.{column} IS NOT NULL AND NOT EXISTS "
            f"(SELECT 1 FROM {parent} p WHERE p.id = t.{column})")
        if rows and rows[0]["c"]:
            found.append({"table": table, "column": column,
                          "parent": parent, "count": rows[0]["c"]})
    return found


def purge():
    """Delete every fixture row. Returns a record of what happened, for evidence."""
    listed = inventory()
    saved = backup()

    db = get_db()
    db.execute("PRAGMA foreign_keys = ON")     # per-connection; cascades need it on

    deleted = {}
    # Customers last: cascading from them removes most dependents, and deleting
    # the leaves first keeps the counts per table honest rather than showing
    # zero for rows a cascade already took.
    order = [t for t in FIXTURE_TABLES if t != "customers"] + ["customers"]
    for table in order:
        before = query(f"SELECT COUNT(*) AS c FROM {table}", one=True)["c"]
        execute(f"DELETE FROM {table} WHERE is_fixture = 1")
        after = query(f"SELECT COUNT(*) AS c FROM {table}", one=True)["c"]
        deleted[table] = before - after

    # Seeded logins belong to seeded customers. A CLIENT user whose customer is
    # gone can still authenticate, which is a live credential attached to
    # nothing — so they go too.
    execute("DELETE FROM users WHERE role = 'CLIENT' AND (customer_id IS NULL OR "
            "customer_id NOT IN (SELECT id FROM customers))")

    left = orphans()
    if left:
        raise RuntimeError(f"purge left orphan rows: {left}")

    remaining = {t: query(f"SELECT COUNT(*) AS c FROM {t} WHERE is_fixture = 1",
                          one=True)["c"] for t in FIXTURE_TABLES}
    return {"inventory": listed, "backup": saved, "deleted": deleted,
            "orphans": left, "remaining_fixtures": remaining}
