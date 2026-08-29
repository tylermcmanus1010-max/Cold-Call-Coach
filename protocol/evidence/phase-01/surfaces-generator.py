"""The canonical surface list, v2 — rebuilt after QA-01 failed clause 1 and clause 3.

What changed and why:
  + python modules      six in-line items were mapped onto module paths that the
                        "complete" census did not contain (QA-01, clause 1).
  + CLI commands        CHG-003's only guard lives in `flask launch`, which was
                        not a surface in v1.
  + the prototype       §1 claimed it was inventoried as one surface. It was not.
  + an `items` column    v1 had no way to say which surfaces carry an in-line item,
                        so "no surface is unmapped" was unanswerable from the data
                        (QA-01, clause 3). Now both readings of that phrase are.
  ~ document rows       all five duplicated a route row. They are kept, because a
                        document is a distinct thing from the route that serves it,
                        but marked `duplicate_of` so the distinct count is honest.
"""
import os, sqlite3
from pathlib import Path
from monti import create_app

app = create_app()

# The item -> surface mapping, stated once. Values are matched against the
# surface name, so a prefix covers a family of routes.
ITEMS = {
    "CHG-001": ["GET /admin/revenue", "monti/templates/admin/revenue.html",
                "monti/static/css/app.css", "monti/analytics.py"],
    "CHG-002": ["GET /admin/revenue", "monti/analytics.py",
                "monti/templates/admin/revenue.html"],
    "CHG-003": ["applications", "catalog_items", "customers", "decision_items",
                "ledger_entries", "orders", "quotes", "monti/purge.py", "monti/seed.py",
                "flask launch", "flask purge-fixtures", "monti/__init__.py"],
    "CHG-004": ["/portal/", "monti/templates/portal/"],
    "CHG-005": ["GET /admin/revenue", "monti/templates/admin/revenue.html",
                "monti/static/css/app.css"],
    "CHG-008": ["GET /admin/revenue", "GET /admin/orders", "monti/analytics.py"],
    "CHG-009": ["GET /admin/revenue", "GET /admin/ledger", "GET /portal/ledger",
                "monti/analytics.py", "monti/ledger.py"],
    "CHG-010": ["GET /admin/revenue", "monti/templates/admin/revenue.html",
                "monti/static/css/app.css"],
    "CHG-011": ["monti/static/css/app.css", "monti/utils.py",
                "monti/templates/", "GET /admin/", "/portal/"],
    "CHG-012": ["monti/templates/_shell.html"],
    "CHG-013": ["monti/static/css/app.css", "monti/templates/"],
    "CHG-014": ["monti/ledger.py", "ledger_entries", "GET /admin/ledger/receipt",
                "GET /portal/ledger/receipt", "Receipt"],
    "CHG-015": ["decision_items", "item_revisions", "item_genome",
                "monti/templates/portal/products.html", "monti/templates/admin/desk.html",
                "monti/genome.py"],
    "CHG-016": ["monti/templates/", "monti/blueprints/", "monti/auth.py", "users", "customers"],
    "CHG-017": ["GET /admin/clients/<int:customer_id>/open", "GET /admin/clients/close",
                "security_log", "monti/blueprints/admin.py", "monti/auth.py",
                "monti/templates/_shell.html"],
}

def items_for(name):
    hits = [cid for cid, pats in ITEMS.items() if any(p in name for p in pats)]
    return ",".join(sorted(hits))

rows = []
route_names = set()
for r in sorted(app.url_map.iter_rules(), key=lambda x: str(x.rule)):
    if r.endpoint == "static":
        continue
    methods = ",".join(sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS")))
    name = f"{methods} {r.rule}"
    route_names.add(str(r.rule))
    rows.append(["route", name, r.endpoint, r.endpoint.split(".")[0], "", items_for(name)])

for p in sorted(Path("monti/templates").rglob("*.html")):
    rel = str(p)
    area = p.parent.name if p.parent.name != "templates" else "shared"
    rows.append(["email" if "/email/" in rel else "template", rel, p.name, area, "", items_for(rel)])

for p in sorted(Path("monti").rglob("*.py")):
    if "__pycache__" in str(p):
        continue
    rel = str(p)
    rows.append(["module", rel, f"{len(p.read_text().splitlines())} lines",
                 p.parent.name, "", items_for(rel)])

con = sqlite3.connect(os.environ["DATABASE_PATH"])
for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
    cols = len(con.execute(f"PRAGMA table_info({n})").fetchall())
    rows.append(["table", n, f"{cols} columns", "data", "", items_for(n)])

for p in sorted(Path("monti/static").rglob("*")):
    if p.is_file():
        rows.append(["static", str(p), f"{p.stat().st_size} bytes", "static", "", items_for(str(p))])

# CLI commands — CHG-003's only guard is one of these.
for cmd, what in [("flask launch", "brings the database to launch state; refuses on fixture customers"),
                  ("flask purge-fixtures", "deletes seeded rows after a verified backup"),
                  ("flask seed", "writes the demo dataset; is_fixture = 1")]:
    rows.append(["cli", cmd, what, "cli", "", items_for(cmd)])

# Documents. Each is served by a route already listed above; kept as its own
# surface because the artifact is not the route, and marked so the count is honest.
for name, rule in [("Receipt PDF/HTML — admin retrieval", "/admin/ledger/receipt/<receipt_no>"),
                   ("Receipt PDF/HTML — client retrieval", "/portal/ledger/receipt/<receipt_no>"),
                   ("Ledger export CSV — admin", "/admin/ledger/export.csv"),
                   ("Ledger export CSV — client", "/portal/ledger/export.csv"),
                   ("Uploaded quote file", "/portal/files/<int:file_id>")]:
    rows.append(["document", name, rule, "documents",
                 f"route {rule}" if rule in route_names else "", items_for(name + " " + rule)])

# The prototype. One surface, out of scope for every in-line item, recorded so the
# census covers the repository rather than only the engine.
pr = Path("../prototype/monti-prototype.html")
rows.append(["prototype", "monti-makes-it/prototype/monti-prototype.html",
             f"{len(pr.read_text().splitlines())} lines, in-memory demo" if pr.exists() else "n/a",
             "prototype", "", ""])

print("\t".join(["kind", "surface", "detail", "area", "duplicate_of", "items"]))
for r in rows:
    print("\t".join(str(x) for x in r))
