"""D-029 — locate and revert the record the Phase 1 impersonation test wrote as Boars Head.

    python d029-revert-probe.py <db> [<db> ...]           report only
    python d029-revert-probe.py --revert <db> [<db> ...]  report, delete, re-report

`monti/intake.py:create_request` writes FIVE rows per submission:

    1 quotes            2 decision_items       3 capacity_ledger
    4 crm_activities    5 calendar_events

The Phase 1 probe's own cleanup deleted the first three and missed the last two, and
then reported "probe rows removed". This searches all five — by the probe's text marker
AND by the references the probe generated, because the calendar row carries neither the
marker nor the item ref, only the quote ref. A search that finds nothing is not proof
that nothing is there if the search was too narrow; that is what went wrong the first
time.
"""
import sqlite3, sys, os

MARK, QREF, DREF = "%baseline write probe%", "%MMI-Q-1001%", "%MMI-D-003%"

PROBES = [
    ("quotes",          "SELECT id, ref, title FROM quotes "
                        "WHERE title LIKE :m OR ref LIKE :q",
                        "DELETE FROM quotes WHERE title LIKE :m OR ref LIKE :q"),
    ("decision_items",  "SELECT id, ref, auto_name FROM decision_items "
                        "WHERE auto_name LIKE :m OR ref LIKE :d OR source LIKE :m",
                        "DELETE FROM decision_items WHERE auto_name LIKE :m OR ref LIKE :d OR source LIKE :m"),
    ("capacity_ledger", "SELECT id, label FROM capacity_ledger WHERE label LIKE :m",
                        "DELETE FROM capacity_ledger WHERE label LIKE :m"),
    ("crm_activities",  "SELECT id, customer_id, body FROM crm_activities "
                        "WHERE body LIKE :m OR body LIKE :q OR body LIKE :d",
                        "DELETE FROM crm_activities WHERE body LIKE :m OR body LIKE :q OR body LIKE :d"),
    ("calendar_events", "SELECT id, customer_id, title FROM calendar_events "
                        "WHERE title LIKE :m OR title LIKE :q OR title LIKE :d",
                        "DELETE FROM calendar_events WHERE title LIKE :m OR title LIKE :q OR title LIKE :d"),
]
ARGS = {"m": MARK, "q": QREF, "d": DREF}

def scan(con, tables, show=True):
    total = 0
    for name, sel, _ in PROBES:
        if name not in tables:
            continue
        rows = con.execute(sel, ARGS).fetchall()
        total += len(rows)
        if show:
            print(f"   {name:17} {len(rows)} row(s)")
            for r in rows:
                print(f"       {r}")
    return total

revert = "--revert" in sys.argv
paths = [a for a in sys.argv[1:] if a != "--revert"]

print("# D-029 — impersonation test residue on Boars Head (MMI-C-1001)")
print(f"# mode: {'REVERT' if revert else 'report only'}")
print()
grand_before = grand_after = 0
for path in paths:
    print(f"## {path}")
    if not os.path.exists(path):
        print("   does not exist\n"); continue
    con = sqlite3.connect(path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    try:
        cl = con.execute("SELECT ref, company_name FROM customers ORDER BY id LIMIT 3").fetchall()
        n = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        print(f"   customers: {n}  ({', '.join(f'{r}/{c}' for r, c in cl)}"
              f"{', ...' if n > 3 else ''})")
    except sqlite3.Error:
        print("   customers: table absent")
    print("   BEFORE:")
    before = scan(con, tables)
    grand_before += before
    if revert and before:
        for name, _, dele in PROBES:
            if name in tables:
                con.execute(dele, ARGS)
        con.commit()
        print("   AFTER the revert:")
        after = scan(con, tables)
        grand_after += after
    elif revert:
        grand_after += 0
    print(f"   -> {before} residue row(s)"
          + (f", {grand_after} remaining" if revert and before else ""))
    print()

print(f"TOTAL found: {grand_before}" + (f" · TOTAL remaining after revert: {grand_after}" if revert else ""))
