"""CHG-014 baseline — receipts, credit notes, immutability, PDF export."""
import inspect, re
from pathlib import Path
import monti.ledger as L

print("# CHG-014 baseline — the document engine as it stands")
print()
print("## What exists in monti/ledger.py")
fns = [n for n, o in vars(L).items() if inspect.isfunction(o) and not n.startswith("_")]
print("  public functions:", ", ".join(sorted(fns)))
print()
for clause, probe in [
    ("Exactly one receipt per purchase",      "receipt" in fns or "next_receipt_no" in dir(L)),
    ("Unbroken immutable numbering",          hasattr(L, "next_receipt_no")),
    ("Credit note issuance",                  any("credit" in n for n in fns)),
    ("Refund path",                           any("refund" in n for n in fns)),
    ("Reversal path",                         any("revers" in n for n in fns)),
]:
    print(f"  {clause:40} {'present' if probe else 'ABSENT'}")
print()
print("## PDF export")
libs = []
for lib in ("reportlab", "weasyprint", "fpdf", "xhtml2pdf", "pdfkit"):
    try:
        __import__(lib); libs.append(lib)
    except ImportError:
        pass
print("  PDF libraries importable:", libs or "NONE")
req = Path("requirements.txt")
print("  requirements.txt:", " ".join(req.read_text().split()) if req.exists() else "(missing)")
src = " ".join(p.read_text() for p in Path("monti").rglob("*.py"))
print("  'application/pdf' anywhere in monti/:", "application/pdf" in src)
print()
print("## Retrieval routes")
print("  GET /portal/ledger/receipt/<receipt_no>   client — scoped by customer_id (ledger.receipt)")
print("  GET /admin/ledger/receipt/<receipt_no>    admin  — unscoped")
print("  'Admin retrieval logged' clause: the only skill that logs admin access to a")
print("  client's record is SK-37, ACTIVE as of D-001 and landing at Phase 8. Phase 16")
print("  (documents) comes after Phase 8, so the ordering works.")
print()
print("## Immutability")
# The first version of this line read `\\s+FROM?\\s*` — which is UPDATE, whitespace,
# then the literal "FRO" with an optional "M". It could never match "UPDATE
# ledger_entries" and reported "none found" over two real statements. SK-30 is
# non-waivable and this probe is the basis for one of its clauses, so it now
# matches both statement shapes and prints what it finds.
edits = re.findall(r"(?:UPDATE\s+(ledger_entries)|DELETE\s+FROM\s+(ledger_entries))", src, re.I)
edit_sites = []
for f in sorted(Path("monti").rglob("*.py")):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        if re.search(r"UPDATE\s+ledger_entries|DELETE\s+FROM\s+ledger_entries", line, re.I):
            edit_sites.append(f"{f}:{i}  {line.strip()[:88]}")
print(f"  UPDATE/DELETE statements against ledger_entries in monti/: {len(edit_sites)}")
for site in edit_sites:
    print(f"    {site}")
if edit_sites:
    print("  Both transition a PENDING row to SETTLED or FAILED — a pending payment")
    print("  resolving, not an issued receipt being edited. Corrections to settled money")
    print("  go through ledger.reverse, which writes a linked reversing row. The clause")
    print("  below therefore rests on an argument, not on an absence, and Phase 16 must")
    print("  prove it rather than inherit it.")
print("  ledger.reverse present:", hasattr(L, "reverse"), "— corrections as linked reversing rows")
print()
print("## Against CHG-014's gate")
for clause, state in [
    ("Exactly one receipt per purchase",                       "partly — receipts exist, one-per-purchase not asserted anywhere"),
    ("Unbroken immutable numbering",                           "numbering exists (next_receipt_no); 'unbroken' is unasserted"),
    ("Regenerates byte-identical from stored order data",      "UNBUILT — no regeneration path"),
    ("Totals reconcile to the order and both ledgers",         "built — A32/A34 in the existing suite"),
    ("No code path edits or deletes an issued receipt",        "holds by argument, not by absence — see the two UPDATEs above"),
    ("Refund yields original + credit note + correct net",     "UNBUILT — no credit note anywhere in code or schema"),
    ("Both exporting as PDF",                                  "UNBUILT — no PDF library, no application/pdf"),
    ("Clients retrieve only their own",                        "built — ledger.receipt scopes by customer_id"),
    ("Admin retrieval logged",                                 "UNBUILT — security_log unwritten (see CHG-017)"),
]:
    print(f"  {clause:56} {state}")
