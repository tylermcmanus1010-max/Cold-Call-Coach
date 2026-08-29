"""CHG-003 baseline — fixture data, and whether a standing guard exists."""
import os, sqlite3
from pathlib import Path

con = sqlite3.connect(os.environ["DATABASE_PATH"])
print("# CHG-003 baseline — fixture data and the standing guard")
print()
print("## Tables carrying an is_fixture marker")
marked, unmarked = [], []
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    (marked if "is_fixture" in cols else unmarked).append(t)
print(f"  with is_fixture: {len(marked)}  {', '.join(marked)}")
print(f"  without:         {len(unmarked)}  — on these a fixture row is not nameable")
print()
print("## Fixture rows on this database")
total = sum(con.execute(f"SELECT COUNT(*) FROM {t} WHERE is_fixture = 1").fetchone()[0] for t in marked)
print(f"  TOTAL fixture rows: {total}")
print()
print("## Rows present (this is a launched database — one real client)")
for t in ("customers", "users", "catalog_items", "orders", "quotes",
          "decision_items", "ledger_entries", "client_agents"):
    print(f"  {t:18} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
print("  NOTE: a bare `flask launch` creates ONE user, the admin. Any member user")
print("  present was added by whoever ran the render census, not by launch.")
print()
print("## The standing guard")
src = Path("monti/__init__.py").read_text()
i = src.find("Fixture rows are still present")
print("  monti/__init__.py:100 — the only guard. `flask launch` refuses to run when a")
print("  customer carries is_fixture = 1:")
print(f'    "{src[i:i+90]}..."')
print("  It fires once, at launch, on one table. Nothing refuses a fixture row at write")
print("  time on any table, and 38 of the 45 tables carry no marker at all.")
print("  monti/seed.py writes is_fixture = 1 deliberately; monti/purge.py deletes and")
print("  sweeps orphans. Neither is a guard.")
print()
print("  CHG-003's third gate clause — 'the guard fires on a deliberately reintroduced")
print("  fixture row' — is therefore met only for `flask launch` and only for customers.")
print("  DATAOPS-01 owns SK-38 and calls this gate at Phase 2.")
