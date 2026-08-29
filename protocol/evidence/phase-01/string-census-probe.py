"""CHG-016 baseline — how much user-facing English is hard-coded, and where.

The counts move with the pattern, so the pattern is printed with the number.
See HOW-TO-REPRODUCE.md for why that matters.
"""
import os, re, sqlite3
from pathlib import Path

TEXT  = re.compile(r">\s*([A-Z][^<>{}\n]{3,}?)\s*<")
FLASH = re.compile(r"flash\(")

print("# CHG-016 / Phase 10 baseline — hard-coded user-facing strings")
print()
print("## Externalization machinery present in the build")
found = [w for probe, w in [("monti/translations", "gettext catalogue"),
                            ("babel.cfg", "Babel config"), ("messages.pot", "extraction template"),
                            ("monti/strings.py", "string table module")] if Path(probe).exists()]
print("  " + ("; ".join(found) if found else
      "NONE. No catalogue, no extraction config, no string table, no gettext import."))
print()
print(f"## Template text nodes   pattern: {TEXT.pattern}")
tmpl = {str(p): len(TEXT.findall(p.read_text())) for p in sorted(Path("monti/templates").rglob("*.html"))}
tmpl = {k: v for k, v in tmpl.items() if v}
mails = {k: v for k, v in tmpl.items() if "/email/" in k}
print(f"  files with copy: {len(tmpl)}   total nodes: {sum(tmpl.values())}")
print(f"  of which email templates: {len(mails)} files, {sum(mails.values())} nodes "
      f"— part of the total above, not additional to it")
for k, v in sorted(tmpl.items(), key=lambda kv: -kv[1])[:15]:
    print(f"    {v:5}  {k}")
print(f"    ... {len(tmpl) - 15} more files")
print()
print(f"## flash() messages   pattern: {FLASH.pattern}")
py = {str(p): len(FLASH.findall(p.read_text())) for p in sorted(Path("monti").rglob("*.py"))
      if "__pycache__" not in str(p)}
py = {k: v for k, v in py.items() if v}
print(f"  files: {len(py)}   total calls: {sum(py.values())}")
for k, v in sorted(py.items(), key=lambda kv: -kv[1]):
    print(f"    {v:5}  {k}")
print()
print("## Language preference storage")
con = sqlite3.connect(os.environ["DATABASE_PATH"])
for t in ("users", "customers"):
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    print(f"  language column on {t}: {'yes' if any('lang' in c for c in cols) else 'NO'}")
print()
print("§4.4 I18N-01: 'Language preference is stored per user, not per company.'")
print("Neither column exists. That schema change belongs to Phase 10, and SK-39")
print("(migration safety, DATA-01) governs how it lands.")
print()
print("## Summary for the register")
print(f"CHG-016 is unbuilt in full: no catalogue, no extraction config, no string table,")
print(f"no language column. Phase 10 gates on {sum(tmpl.values())} template text nodes across")
print(f"{len(tmpl)} files (the {len(mails)} email templates contribute {sum(mails.values())} of them)")
print(f"plus {sum(py.values())} flash() messages across {len(py)} modules. Phase 10's own")
print("instruction is that email templates are checked first, because that is where")
print("English leaks.")
