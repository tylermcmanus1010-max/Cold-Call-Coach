"""A06 — the brand and claim scanner.

Two things fail this check: the old brand surviving anywhere, and a sentence
claiming we own the factory. §1.5 lists both as banned strings, and the reason
the second is banned is recorded there: the facility is in China, the ownership
a Western reader infers from "we own it" does not straightforwardly exist there,
and the accurate claim — that we are the manufacturer — is the stronger one
anyway.

Greping the repository is not sufficient (§7.1). A rename that misses the
database is not a rename, and a rename that misses what the app actually renders
is not a rename either. So this scans three surfaces:

    source      every tracked text file, plus asset *filenames*
    database    every text column of every table, which is where seeded copy,
                settings rows and stored email templates live
    output      what the app renders — every public route, a member's portal, an
                admin page — and the body of every email it has sent

The third is what catches a banned string assembled at runtime from parts that
are each individually clean.
"""
import re
import sqlite3
from pathlib import Path

from . import Check, Finding

ENGINE_DIR = Path(__file__).resolve().parent.parent.parent

# §1.5, verbatim. Matched case-insensitively, on any surface.
BANNED = [
    "we own the factory",
    "our own factory",
    "factory we own",
    "owned and operated",
    "ownership of the manu",
    "our factory in china",
    "we own the manufactur",
    "wholly owned",
    "our facility in china",
    "montano makes that",
    "montano",
    "mmt",
]

def _compile(phrase):
    """A banned phrase, matched the way it actually appears in the wild.

    Spaces are elastic, so "montano makes that" is also caught in
    `montanomakesthat.com` and in `montano-makes-that.zip`. Only "mmt" gets a
    trailing boundary: three letters with no boundary would fire inside
    unrelated identifiers, whereas the brand words are matched loosely on
    purpose — a domain name is exactly where a rename gets missed.
    """
    core = r"[\s\-_]*".join(re.escape(word) for word in phrase.split())
    trailing = r"(?![a-z0-9])" if phrase == "mmt" else ""
    return re.compile(r"(?<![a-z0-9])" + core + trailing, re.I)


_PATTERNS = [(phrase, _compile(phrase)) for phrase in BANNED]

SCAN_EXTENSIONS = {
    ".py", ".html", ".css", ".js", ".sql", ".md", ".txt", ".json", ".yml", ".yaml",
    ".cfg", ".ini", ".toml", ".example", ".svg", ".csv",
}
SKIP_DIRS = {".git", ".venv", "__pycache__", "instance", "node_modules", "evidence"}

# The protocol document quotes every banned string in order to ban it, and this
# scanner names them for the same reason. Neither ships to a client.
SELF_REFERENTIAL = {"PROTOCOL.md", "brand.py", "brand-inventory.csv"}


def _hits(text):
    """Every banned phrase in `text`, as (phrase, offset).

    "montano makes that" and "montano" both match the same eighteen characters.
    Reporting one occurrence twice would inflate the inventory and make the
    fix-and-recount loop lie, so overlapping matches collapse to the longest.
    """
    spans = []
    for phrase, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end(), phrase))
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))

    kept = []
    for start, end, phrase in spans:
        if any(start >= k_start and end <= k_end for k_start, k_end, _ in kept):
            continue
        kept.append((start, end, phrase))
    return [(phrase, start) for start, _, phrase in kept]


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def scan_source(root=None):
    """Banned strings in tracked text, and in asset filenames (§7.1)."""
    root = Path(root or ENGINE_DIR)
    findings = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root)

        # An asset filename carrying the old brand fails too (WI-B-05).
        for phrase, _ in _hits(path.name):
            findings.append(Finding(str(rel), f"filename carries {phrase!r}"))

        if path.name in SELF_REFERENTIAL or path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for phrase, offset in _hits(text):
            findings.append(
                Finding(f"{rel}:{_line_of(text, offset)}", f"banned string {phrase!r}"))
    return findings


def scan_database(db_path):
    """Every text column of every table. A rename that misses the DB is not one."""
    findings = []
    if not Path(db_path).exists():
        return findings
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
            if not cols:
                continue
            for row in conn.execute(f"SELECT rowid, * FROM {table}"):
                for col in cols:
                    value = row[col]
                    if not isinstance(value, str):
                        continue
                    for phrase, _ in _hits(value):
                        findings.append(Finding(
                            f"db:{table}.{col}#{row['rowid']}", f"banned string {phrase!r}"))
    finally:
        conn.close()
    return findings


def scan_rendered(client, routes):
    """What the app actually sends. Catches a string assembled at runtime."""
    findings = []
    for route in routes:
        try:
            response = client.get(route, follow_redirects=True)
        except Exception as exc:                       # a route that 500s is its own defect
            findings.append(Finding(f"render:{route}", f"did not render: {exc}"))
            continue
        body = response.get_data(as_text=True)
        for phrase, offset in _hits(body):
            findings.append(Finding(
                f"render:{route}:{_line_of(body, offset)}", f"banned string {phrase!r}"))
    return findings


def scan_emails(db_path):
    """Sent email bodies and subject lines — generated output, not the template."""
    findings = []
    if not Path(db_path).exists():
        return findings
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT id, to_addr, subject, body FROM email_log").fetchall()
    except sqlite3.OperationalError:
        return findings
    finally:
        conn.close()
    for row in rows:
        for field in ("subject", "body", "to_addr"):
            value = row[field] or ""
            for phrase, _ in _hits(value):
                findings.append(Finding(
                    f"email#{row['id']}.{field}", f"banned string {phrase!r} in a sent email"))
    return findings


def run(ctx):
    return (scan_source()
            + scan_database(ctx.db_path)
            + scan_rendered(ctx.public_client, ctx.public_routes)
            + scan_rendered(ctx.member_client, ctx.member_routes)
            + scan_rendered(ctx.admin_client, ctx.admin_routes)
            + scan_emails(ctx.db_path))


def prove(ctx):
    """Three deliberate defects, one per surface, each reverted.

    §7.1 is explicit that a scan which only greps the repository is not
    sufficient, so the proof has to demonstrate a catch in the database and in
    rendered output as well as in a file.
    """
    caught = []

    # 1. source — a banned string in a template
    target = ENGINE_DIR / "monti" / "templates" / "public" / "home.html"
    original = target.read_text()
    target.write_text(original.replace("</section>", "<p>we own the factory</p></section>", 1))
    try:
        hit = [f for f in scan_source() if "home.html" in f.where]
        caught.append(("source: 'we own the factory' in home.html", bool(hit),
                       hit[0].where if hit else None))
    finally:
        target.write_text(original)

    # 2. database — a banned string in seeded content
    conn = sqlite3.connect(ctx.db_path)
    conn.execute("INSERT INTO settings (key, value) VALUES ('_proof', 'Montano Makes That')")
    conn.commit()
    try:
        hit = [f for f in scan_database(ctx.db_path) if "settings" in f.where]
        caught.append(("database: old brand in settings.value", bool(hit),
                       hit[0].where if hit else None))
    finally:
        conn.execute("DELETE FROM settings WHERE key = '_proof'")
        conn.commit()
        conn.close()

    # 3. rendered output — a string that exists in no file, only in what is sent
    ctx.app.config["COMPANY_NAME"] = "Montano Makes That"
    try:
        hit = scan_rendered(ctx.public_client, ["/"])
        caught.append(("rendered: old brand injected into config, not source", bool(hit),
                       hit[0].where if hit else None))
    finally:
        ctx.app.config["COMPANY_NAME"] = ctx.company_name

    missed = [name for name, ok, _ in caught if not ok]
    detail = "; ".join(f"{name} -> {where or 'MISSED'}" for name, _, where in caught)
    return (not missed), detail


CHECKS = [Check("A06", "Brand and claim scanner (source, database, rendered, email)",
                run, prove)]
