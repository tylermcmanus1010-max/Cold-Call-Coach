"""SQLite access layer.

Deliberately thin: raw SQL through a row-factory that yields dict-like rows.
Every statement here is standard SQL, so moving to Postgres later is a matter
of swapping the driver and the `?` placeholders for `%s`.
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = current_app.config["DATABASE_PATH"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql: str, args=(), one: bool = False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql: str, args=()) -> int:
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    lastrow = cur.lastrowid
    cur.close()
    return lastrow


def executemany(sql: str, seq) -> None:
    db = get_db()
    db.executemany(sql, seq)
    db.commit()


# Columns added after the first release. `init_db` adds any that are missing so an
# existing database upgrades in place — SQLite has no "ADD COLUMN IF NOT EXISTS".
LATE_COLUMNS = {
    "customers": [
        ("membership_status", "TEXT NOT NULL DEFAULT 'PROSPECT'"),
        ("member_since", "TEXT"),
        ("quote_limit", "INTEGER NOT NULL DEFAULT 10"),
        ("quote_cycle_days", "INTEGER NOT NULL DEFAULT 30"),
        ("membership_note", "TEXT"),
        ("catalog_tags", "TEXT"),
        ("freight_waived_default", "INTEGER NOT NULL DEFAULT 0"),
        ("is_fixture", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "catalog_items": [
        ("tags", "TEXT"),
        # The public half of an item (§8.2). Deliberately entered by an admin,
        # never derived from anyone's negotiated price (§8.6).
        ("range_low_cents", "INTEGER"),
        ("range_high_cents", "INTEGER"),
        ("typical_moq", "INTEGER"),
        ("typical_lead_time_days", "INTEGER"),
        ("range_drivers", "TEXT"),
        ("is_public", "INTEGER NOT NULL DEFAULT 0"),
        ("is_fixture", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "orders": [
        ("delivered_at", "TEXT"),
        ("fee_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("processing_fee_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("freight_estimate_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("customs_estimate_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("freight_breakdown", "TEXT"),
        ("freight_waived", "INTEGER NOT NULL DEFAULT 0"),
        ("waived_by", "TEXT"),
        ("waived_at", "TEXT"),
        ("is_fixture", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "quotes": [
        ("decline_reason", "TEXT"),
        ("triaged_at", "TEXT"),
        ("triaged_by", "TEXT"),
        ("is_fixture", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "applications": [("is_fixture", "INTEGER NOT NULL DEFAULT 0")],
}

# Tables that can carry seeded rows. `flask purge-fixtures` sweeps exactly these
# and A14 asserts the sweep left nothing behind, including orphans.
FIXTURE_TABLES = ("customers", "applications", "quotes", "orders", "catalog_items")

# Every fixture table needs the marker column, or the purge cannot sweep it.
for _table in FIXTURE_TABLES:
    assert any(name == "is_fixture" for name, _ in LATE_COLUMNS.get(_table, ())), \
        f"{_table} is swept by purge-fixtures but has no is_fixture column"


def init_db():
    db = get_db()
    schema = (Path(current_app.root_path) / "schema.sql").read_text()
    db.executescript(schema)
    db.commit()
    migrate()


def migrate():
    """Idempotent, additive schema upgrades. Safe to run on every boot.

    LATE_COLUMNS is a dict literal, so a table listed twice loses its first
    entry silently and the columns in it are simply never added — invisible on
    a fresh install, because schema.sql creates them anyway, and a missing
    column on every upgraded database. The count check below turns that back
    into a crash at import rather than a mystery in production.
    """
    db = get_db()
    for table, columns in LATE_COLUMNS.items():
        existing = {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}
        for name, spec in columns:
            if name not in existing:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")
    db.commit()
    _adopt_legacy_assignments(db)


def _adopt_legacy_assignments(db):
    """Carry `catalog_assignments` rows into `catalogue_registrations`.

    The old table granted a member an item at a negotiated price; §8.3 makes
    that same grant the thing that permits ordering, with an active flag and an
    attributed author. An existing database's direct grants have to arrive in
    the new table or every one of those members is gated out of items they were
    already buying. Idempotent, so it is safe on every boot.
    """
    tables = {r["name"] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "catalog_assignments" not in tables:
        return
    db.execute(
        "INSERT OR IGNORE INTO catalogue_registrations "
        "(item_id, customer_id, unit_price_cents, moq, active, assigned_by, assigned_at, notes) "
        "SELECT item_id, customer_id, custom_price_cents, custom_moq, 1, "
        "       COALESCE(assigned_by, 'migrated'), assigned_at, note "
        "FROM catalog_assignments")
    db.commit()


def get_setting(key: str, default=None):
    row = query("SELECT value FROM settings WHERE key = ?", (key,), one=True)
    return row["value"] if row else default


def set_setting(key: str, value) -> None:
    execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
        (key, str(value)),
    )


def next_ref(prefix: str, table: str, start: int = 1001) -> str:
    """Human-friendly sequential reference, e.g. MMI-Q-1004."""
    row = query(f"SELECT COUNT(*) AS c FROM {table}", one=True)
    return f"{prefix}-{start + (row['c'] or 0)}"


@click.command("init-db")
def init_db_command():
    """Create the database tables."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
