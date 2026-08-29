"""The canonical surface list. Run from monti-makes-it/engine with DATABASE_PATH set.

    PYTHONPATH=. DATABASE_PATH=<a launched db> python surfaces-generator.py > surfaces.tsv

Columns: kind, surface, detail, area, duplicate_of, items

The `items` column is DERIVED FROM CONTENT, not from path prefixes. The first two
versions of this file matched item patterns against the surface *name*, which gave
CHG-011 all 81 templates (46 of which render no currency at all) while missing the
two share-bar templates for CHG-005, the receipt templates for CHG-014, and a
repeated primary button in admin/catalog_detail.html for CHG-010. QA-01 failed the
phase on it twice. Each rule below now opens the file and looks.
"""
import os, re, sqlite3
from pathlib import Path
from monti import create_app

app = create_app()
ROOT = Path(".")

def read(p):
    try:
        return Path(p).read_text()
    except Exception:
        return ""

# --- content probes -------------------------------------------------------
MONEY   = re.compile(r"\|money|'%\.[24]f'\s*\|\s*format|/ 100\b")
HEX     = re.compile(r"#[0-9a-fA-F]{3,8}\b")
STATUS  = re.compile(r"var\(--(good|warn|crit|stop|wait|red|amber)\)|badge-(green|red|amber)")
TEXT    = re.compile(r">\s*([A-Z][^<>{}\n]{3,}?)\s*<")
FLASH   = re.compile(r"flash\(")
# a filled primary button inside a row of a loop — CHG-010's stated defect
ROWBTN  = re.compile(r"<a[^>]*class=\"[^\"]*btn[^\"]*\"[^>]*>(?:(?!</a>).)*</a>", re.S)

TEMPLATES = sorted(Path("monti/templates").rglob("*.html"))
# Every Python module in the engine, not just monti/. The first two versions took
# monti/*.py plus app.py and left tests/ out — while document-baseline.txt scores two
# CHG-014 gate clauses against tests/ and requirements.txt. QA-01 failed clause 1 on
# that same shape three times; the fix is to walk the tree rather than name the parts.
MODULES = [p for p in sorted(Path(".").rglob("*.py"))
           if "__pycache__" not in str(p) and ".venv" not in str(p)]

def template_items(p):
    src, rel, out = read(p), str(p), set()
    if MONEY.search(src):                                   out.add("CHG-011")
    if HEX.search(src) or STATUS.search(src):                out.add("CHG-013")
    if TEXT.search(src):                                     out.add("CHG-016")
    if 'class="meter' in src:                                out.add("CHG-005")
    if "{% for" in src and ROWBTN.search(src) and "<td" in src: out.add("CHG-010")
    if rel.startswith("monti/templates/portal/"):            out.add("CHG-004")
    if "chart-bar" in src or "chart-svg" in src:             out.update({"CHG-001", "CHG-002", "CHG-008"})
    if "range-btn" in src or "periods" in src:               out.add("CHG-009")
    if "auth.logout" in src:                                 out.add("CHG-012")
    if "viewing_as" in src:                                  out.add("CHG-017")
    if "receipt" in rel or "receipt" in src.lower():          out.add("CHG-014")
    if "revision" in src.lower() or "genome" in rel:          out.add("CHG-015")
    return out

def module_items(p):
    src, rel, out = read(p), str(p), set()
    if rel.startswith("tests/"):
        # The suite is a surface: CHG-014's gate is scored partly against A32/A34.
        if "ledger" in rel or "money" in rel:  out.add("CHG-014")
        if "tenancy" in rel or "agents" in rel: out.add("CHG-017")
        if "provenance" in rel or "tooling" in rel: out.add("CHG-001")
        return out
    if FLASH.search(src):                                    out.add("CHG-016")
    if "analytics" in rel:                    out.update({"CHG-001", "CHG-002", "CHG-008", "CHG-009"})
    if "ledger" in rel:                       out.update({"CHG-009", "CHG-014"})
    if "genome" in rel or "decisionroom" in rel:             out.add("CHG-015")
    if "is_fixture" in src:                                  out.add("CHG-003")
    if "view_as" in src or "viewing_as" in src or "security_log" in src: out.add("CHG-017")
    if "money" in src and "def money" in src:                out.add("CHG-011")
    return out

TABLE_ITEMS = {
    "customers": {"CHG-003", "CHG-016"}, "users": {"CHG-016"},
    "applications": {"CHG-003"}, "catalog_items": {"CHG-003"}, "orders": {"CHG-003"},
    "quotes": {"CHG-003"}, "decision_items": {"CHG-003", "CHG-015"},
    "ledger_entries": {"CHG-003", "CHG-014", "CHG-009"},
    "item_revisions": {"CHG-015"}, "item_genome": {"CHG-015"},
    "security_log": {"CHG-017"},
}

def route_items(rule, endpoint):
    out = set()
    r = str(rule)
    if r.startswith("/portal"):                              out.add("CHG-004")
    if r == "/admin/revenue":     out.update({"CHG-001", "CHG-002", "CHG-005", "CHG-008", "CHG-009", "CHG-010"})
    if "ledger" in r:                                        out.add("CHG-009")
    if "receipt" in r:                                       out.add("CHG-014")
    if "clients/" in r:                                      out.add("CHG-017")
    return out

rows, route_rules = [], set()
for r in sorted(app.url_map.iter_rules(), key=lambda x: str(x.rule)):
    if r.endpoint == "static":
        continue
    methods = ",".join(sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS")))
    route_rules.add(str(r.rule))
    rows.append(["route", f"{methods} {r.rule}", r.endpoint, r.endpoint.split(".")[0],
                 "", ",".join(sorted(route_items(r.rule, r.endpoint)))])

for p in TEMPLATES:
    rel = str(p)
    kind = "email" if "/email/" in rel else "template"
    area = p.parent.name if p.parent.name != "templates" else "shared"
    rows.append([kind, rel, p.name, area, "", ",".join(sorted(template_items(p)))])

for p in MODULES:
    rows.append(["module", str(p), f"{len(read(p).splitlines())} lines",
                 p.parent.name or "engine", "", ",".join(sorted(module_items(p)))])

rows.append(["schema", "monti/schema.sql", f"{len(read('monti/schema.sql').splitlines())} lines",
             "data", "", "CHG-003,CHG-015,CHG-017"])

# Everything else that is part of the engine and is not code, a template, a table or an
# asset: the packaging files, the docs, and the Phase-0 evidence directory the document
# baseline scores CHG-014 against. Enumerated, not listed.
for p in sorted(Path(".").iterdir()):
    if p.is_file() and p.suffix not in (".py",) and p.name != "surfaces.tsv":
        rows.append(["config", str(p), f"{p.stat().st_size} bytes", "engine", "",
                     "CHG-014" if p.name == "requirements.txt" else ""])
for p in sorted(Path("evidence").glob("*")) if Path("evidence").exists() else []:
    if p.is_file():
        rows.append(["engine-evidence", str(p), f"{len(read(p).splitlines())} lines",
                     "evidence", "", ""])
for p in sorted(Path("..").glob("*.md")):
    if p.is_file():
        rows.append(["doc", f"monti-makes-it/{p.name}", f"{len(read(p).splitlines())} lines",
                     "docs", "", ""])

con = sqlite3.connect(os.environ["DATABASE_PATH"])
for (n,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
    cols = len(con.execute(f"PRAGMA table_info({n})").fetchall())
    rows.append(["table", n, f"{cols} columns", "data", "",
                 ",".join(sorted(TABLE_ITEMS.get(n, set())))])

for p in sorted(Path("monti/static").rglob("*")):
    if p.is_file():
        rel = str(p)
        it = {"CHG-001", "CHG-005", "CHG-010", "CHG-011", "CHG-013"} if rel.endswith("app.css") else set()
        rows.append(["static", rel, f"{p.stat().st_size} bytes", "static", "", ",".join(sorted(it))])

# Every CLI command the app actually registers — read from app.cli, not typed.
CLI_WHAT = {"init-db": "creates the schema and runs migrations",
            "launch": "brings the database to launch state; refuses on fixture customers",
            "purge-fixtures": "deletes seeded rows after a verified backup",
            "seed": "writes the demo dataset; is_fixture = 1"}
for cmd in sorted(app.cli.commands):
    it = "CHG-003" if cmd in ("launch", "purge-fixtures", "seed") else ""
    rows.append(["cli", f"flask {cmd}", CLI_WHAT.get(cmd, ""), "cli", "", it])

for name, rule in [("Receipt document — admin retrieval", "/admin/ledger/receipt/<receipt_no>"),
                   ("Receipt document — client retrieval", "/portal/ledger/receipt/<receipt_no>"),
                   ("Ledger export CSV — admin", "/admin/ledger/export.csv"),
                   ("Ledger export CSV — client", "/portal/ledger/export.csv"),
                   ("Uploaded quote file", "/portal/files/<int:file_id>")]:
    rows.append(["document", name, rule, "documents",
                 f"route {rule}" if rule in route_rules else "",
                 "CHG-014" if "Receipt" in name else ""])

for p in sorted(Path("../prototype").glob("*")):
    if p.is_file():
        rows.append(["prototype", f"monti-makes-it/prototype/{p.name}",
                     f"{len(read(p).splitlines())} lines", "prototype", "", ""])

print("\t".join(["kind", "surface", "detail", "area", "duplicate_of", "items"]))
for r in rows:
    print("\t".join(str(x) for x in r))
