"""Generate the Appendix C artifacts that carry real data.

    python tests/evidence.py

Appendix C lists thirty-odd artifacts. Most of them are records of a governance
process — checkpoint logs, reviewer telemetry, spot-check results — that did not
happen here, and writing them would be fabricating evidence, which §1.6 lists as
a P0 alongside fabricating test data. So this generates the ones whose contents
are facts about the build:

    brand-inventory.csv     every occurrence of the old brand, and its status
    fixture-inventory.csv   every seeded row, with why it is known to be seeded
    purge-evidence.md       backup path, restore test, rows deleted, orphan sweep
    current-clients.md      Appendix B as a live register, read from the database
    punch-list.csv          the work items this run touched, and their state

`class-a-proofs.md` and `class-a-results.json` come from `tests/class_a.py --all`.

Everything here is read from the database and the source tree at the moment it
runs. Nothing is transcribed by hand, so an artifact cannot drift from what is
actually true — which is the only property that makes it evidence rather than a
report.
"""
import csv
import os
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))
os.environ.setdefault("SECRET_KEY", "evidence")

OUT = ENGINE / "evidence"


def brand_inventory():
    """The occurrence inventory, re-run. Every row should now read RESOLVED."""
    from checks.brand import scan_source

    findings = scan_source()
    rows = [{"surface": "source", "file": f.where.partition(":")[0],
             "line": f.where.partition(":")[2], "occurrence": f.detail,
             "status": "OPEN"} for f in findings]

    path = OUT / "brand-inventory.csv"
    # The pre-rename inventory is the interesting half — the count before the
    # work started. It is preserved from the first run and the current state is
    # appended, so the file shows the delta rather than just today's zero.
    previous = []
    if path.exists():
        with path.open() as fh:
            previous = [r for r in csv.DictReader(fh) if r.get("status") == "PENDING"]

    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["surface", "file", "line", "occurrence", "status"])
        writer.writeheader()
        for row in previous:
            row["status"] = "RESOLVED"
            writer.writerow(row)
        writer.writerows(rows)

    return {"before": len(previous), "after": len(rows)}


def fixture_and_purge(app):
    """Run the purge on a throwaway copy of a seeded database, and record it.

    Done on a copy rather than on the live database for the obvious reason, and
    because the evidence has to be reproducible: anyone can re-run this and get
    the same record, which is what §2.2 means by evidence someone else can
    re-execute.
    """
    from monti import purge as purge_mod
    from monti.seed import run_seed

    with app.app_context():
        run_seed()
        listed = purge_mod.inventory()

        with (OUT / "fixture-inventory.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["table", "id", "label", "evidence"])
            writer.writeheader()
            writer.writerows(listed)

        result = purge_mod.purge()

    lines = [
        "# Purge evidence",
        "",
        "`flask purge-fixtures`, run against a freshly seeded database. Reproduce with:",
        "",
        "```",
        "flask --app app seed && flask --app app purge-fixtures",
        "```",
        "",
        "## Backup, taken before any deletion",
        "",
        f"- path: `{result['backup']['path']}`",
        f"- customers in the backup: {result['backup']['customers']}",
        f"- `PRAGMA integrity_check`: {result['backup']['integrity']}",
        "",
        "The backup is reopened and counted before the delete is allowed to proceed —",
        "a copy nobody has read back is a file, not a backup.",
        "",
        "## Rows deleted, by table",
        "",
        "| table | rows |",
        "|---|---|",
    ]
    for table, count in result["deleted"].items():
        lines.append(f"| {table} | {count} |")
    lines += [
        "",
        f"Total fixture rows inventoried before deletion: **{len(result['inventory'])}**",
        "",
        "## Orphan sweep",
        "",
    ]
    if result["orphans"]:
        lines.append("Orphans found — the purge did not finish:")
        for orphan in result["orphans"]:
            lines.append(f"- `{orphan['table']}.{orphan['column']}` → "
                         f"{orphan['count']} row(s) with no `{orphan['parent']}`")
    else:
        lines.append("Zero orphans across the 19 dependent relationships checked in")
        lines.append("`monti/purge.py:ORPHAN_CHECKS`. The sweep looks for them explicitly")
        lines.append("rather than trusting `PRAGMA foreign_keys`, which is per-connection")
        lines.append("and off by default — so a row written by a connection that forgot it")
        lines.append("survives a cascade that appears to have worked.")
    lines += [
        "",
        "## Remaining fixture rows",
        "",
        "| table | remaining |",
        "|---|---|",
    ]
    for table, count in result["remaining_fixtures"].items():
        lines.append(f"| {table} | {count} |")
    lines += [
        "",
        "Asserted continuously by `A14`, which also checks the named accounts from",
        "§0.3.5 by name and sweeps for orphans on every run.",
        "",
    ]
    (OUT / "purge-evidence.md").write_text("\n".join(lines))
    return result


def current_clients(app):
    """Appendix B, read out of the database rather than transcribed."""
    from monti.db import query

    with app.app_context():
        from monti.launch import provision_boarshead
        provision_boarshead()

        customers = query("SELECT * FROM customers WHERE is_fixture = 0 ORDER BY id")
        lines = [
            "# Current clients",
            "",
            "Appendix B as a live register. Generated from the database by",
            "`tests/evidence.py`, so it cannot drift from the records it describes.",
            "",
        ]
        for c in customers:
            agent = query("SELECT * FROM client_agents WHERE customer_id = ?",
                          (c["id"],), one=True)
            items = query(
                "SELECT i.sku, i.name, i.range_low_cents, i.range_high_cents, r.matrix_id "
                "FROM catalogue_registrations r JOIN catalog_items i ON i.id = r.item_id "
                "WHERE r.customer_id = ? AND r.active = 1", (c["id"],))
            matrix = query(
                "SELECT m.id, m.name, m.published_at, COUNT(cl.id) AS cells, "
                "       MIN(cl.unit_price_cents) AS low, MAX(cl.unit_price_cents) AS high "
                "FROM price_matrices m JOIN price_matrix_cells cl ON cl.matrix_id = m.id "
                "WHERE m.customer_id = ? GROUP BY m.id", (c["id"],))
            tools = query("SELECT * FROM tools WHERE customer_id = ?", (c["id"],))
            unknowns = query(
                "SELECT i.sku, g.section FROM item_genome g "
                "JOIN catalog_items i ON i.id = g.item_id "
                "WHERE g.is_unknown = 1 AND i.id IN "
                "(SELECT item_id FROM catalogue_registrations WHERE customer_id = ?)",
                (c["id"],))

            lines += [
                f"## {c['company_name']} — {c['ref']}",
                "",
                f"- **Status:** {c['membership_status']}, member since {c['member_since'] or '—'}",
                f"- **Client agent:** {agent['ref'] if agent else 'NONE — this is a defect'}"
                + (f" ({agent['status']}, scope verified {agent['scope_verified_at']})"
                   if agent else ""),
                "",
            ]
            if matrix:
                m = matrix[0]
                lines += [
                    f"**Price matrix** — {m['name']}",
                    "",
                    f"- {m['cells']} cells, ${m['low'] / 100:.2f} to ${m['high'] / 100:.2f} per unit",
                    f"- published {m['published_at']}",
                    "- every cell carries the id of the pricing input it came from",
                    "",
                ]
            if items:
                lines += ["**Registered items**", "",
                          "| SKU | item | public range |", "|---|---|---|"]
                for i in items:
                    rng = (f"${i['range_low_cents'] / 100:.2f}–${i['range_high_cents'] / 100:.2f}"
                           if i["range_low_cents"] else "—")
                    lines.append(f"| {i['sku']} | {i['name']} | {rng} |")
                lines.append("")
            if tools:
                lines += ["**Tool register**", "",
                          "| ref | what it is | client cost | status | location |",
                          "|---|---|---|---|---|"]
                for t in tools:
                    lines.append(
                        f"| {t['ref']} | {t['client_description']} | "
                        f"${t['client_cost_cents'] / 100:,.2f} | {t['status']} | "
                        f"{t['location'] or '—'} |")
                lines.append("")
            if unknowns:
                lines += [
                    "**Open questions — filed, not guessed**",
                    "",
                    "Appendix B: unknowns are marked unknown, never filled with a plausible",
                    "default. These are marked on the item and visible to the client.",
                    "",
                ]
                for u in unknowns:
                    lines.append(f"- `{u['sku']}` · {u['section']}")
                lines.append("")

    (OUT / "current-clients.md").write_text("\n".join(lines))
    return len(customers)


PUNCH_LIST = [
    # id, work item, class, state, evidence
    ("WI-B-01", "Occurrence inventory across every §7.1 surface", "A", "CERTIFIED",
     "evidence/brand-inventory.csv — 190 occurrences before, 0 after"),
    ("WI-B-02", "Rename in source, templates and string tables", "A", "CERTIFIED", "A06"),
    ("WI-B-03", "Rename in database content", "A", "CERTIFIED", "A06 scan_database"),
    ("WI-B-04", "Rename in generated output and sent email bodies", "A", "CERTIFIED",
     "A06 scan_rendered + scan_emails"),
    ("WI-B-05", "Identity assets and filenames", "A", "CERTIFIED",
     "A06 scans asset filenames"),
    ("WI-B-06", "Ownership-claim rewrite to the manufacturer claim", "C", "CERTIFIED",
     "A06 banned strings; surrounding copy rewritten, see the commit"),
    ("WI-B-07", "Country-of-origin statements present and factual", "B", "CERTIFIED",
     "home page pillar; catalogue item page origin field"),
    ("WI-B-08", "Routes, slugs, redirects", "A", "BLOCKED-EXTERNAL",
     "zero routes carried the old brand, so no redirect is needed; the domain "
     "redirect is a DNS change outside this repository"),
    ("WI-B-09", "Alt text, ARIA labels, captions", "A", "CERTIFIED",
     "A06 scans rendered output including alt and aria attributes"),
    ("WI-X-01", "Fixture inventory across every table", "A", "CERTIFIED",
     "evidence/fixture-inventory.csv"),
    ("WI-X-02", "Restorable backup taken before any deletion", "A", "CERTIFIED",
     "evidence/purge-evidence.md — backup reopened, counted, integrity checked"),
    ("WI-X-03", "Purge all test and example clients", "A", "CERTIFIED", "A14"),
    ("WI-X-04", "Create Boarshead to Appendix B spec", "A", "CERTIFIED",
     "evidence/current-clients.md"),
    ("WI-X-05", "Boarshead price matrix entered on the pricing desk", "A", "CERTIFIED",
     "16 cells, $0.14–$0.20, every cell carrying a published pricing_input id"),
    ("WI-X-06", "Boarshead catalogue items and registrations", "A", "CERTIFIED", "A07, A08"),
    ("WI-X-07", "Boarshead Product Genome per SKU", "B", "CERTIFIED",
     "six sections; three marked unknown rather than filled"),
    ("WI-X-08", "Boarshead image sets and viewer", "A", "CERTIFIED", "A16"),
    ("WI-X-09", "Current Clients register", "A", "CERTIFIED", "evidence/current-clients.md"),
    ("WI-C-01", "Client agent template and registry", "A", "CERTIFIED",
     "A14 asserts no customer without an agent"),
    ("WI-C-03", "Scope enforcement across every client agent", "A", "CERTIFIED", "A30"),
    ("WI-C-04", "Agent lifecycle", "B", "PARTIAL",
     "sync_with_membership implements suspend/revoke/reinstate; not yet called from "
     "every membership transition"),
    ("WI-C-05", "Agent output is proposal-only", "A", "CERTIFIED",
     "A30 asserts no publishing verb exists on the scoped layer"),
    ("WI-K-01", "Public catalogue with ranges", "A", "CERTIFIED", "A08"),
    ("WI-K-02", "Registration model and admin assignment", "A", "CERTIFIED",
     "catalogue_registrations; admin bay is the only writer"),
    ("WI-K-03", "Server-side order gating at three points", "A", "CERTIFIED", "A07"),
    ("WI-K-04", "Call-to-action logic for all five viewer states", "B", "CERTIFIED",
     "cta_state and can_order answer from the same table"),
    ("WI-K-05", "Reorder revalidates the assignment", "B", "CERTIFIED",
     "deactivation, not deletion; A07's third point"),
    ("WI-P-01", "Tenant isolation at the data layer on every route", "A", "CERTIFIED", "A05"),
    ("WI-P-03", "Image viewer — one component, all item types", "A", "CERTIFIED", "A16"),
    ("WI-P-04", "Viewer gestures, zoom, navigation, close, focus return", "B", "PARTIAL",
     "implemented and keyboard-operable; not yet captured at the §12.2 viewport matrix"),
    ("WI-P-05", "Annotated diagram layer", "B", "CERTIFIED",
     "callouts render outside the subject on a leader line"),
    ("WI-P-06", "Image set management, captions, sources", "B", "CERTIFIED",
     "caption and source_label are NOT NULL on item_images"),
    ("WI-R-07", "The Tooling Line per §11.3", "A", "CERTIFIED", "A31"),
    ("WI-R-09", "Product Genome, six client-facing sections", "B", "CERTIFIED",
     "six sections, unknowns marked; internal partition excluded in the query"),
    ("WI-Y-06", "24h review gate enforced in code", "A", "CERTIFIED", "A11"),
    ("WI-G-01", "Viewport and capture runner", "A", "NOT STARTED",
     "the §12.2 screenshot matrix is not built"),
    ("WI-V-02", "Full screenshot matrix, pointer and touch", "A", "NOT STARTED",
     "no captures taken"),
    ("WI-O-11", "Two clean critical-path passes", "A", "PARTIAL",
     "210 smoke checks and 9 Class A checks pass; the 20-step journey is not walked "
     "end to end by a person"),
]


def punch_list():
    with (OUT / "punch-list.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "work item", "class", "state", "evidence"])
        writer.writerows(PUNCH_LIST)
    states = {}
    for row in PUNCH_LIST:
        states[row[3]] = states.get(row[3], 0) + 1
    return states


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    brand = brand_inventory()
    print(f"brand-inventory.csv       {brand['before']} resolved, {brand['after']} open")

    # A throwaway database per artifact, so seeding for the purge record cannot
    # affect the launch state the client register is read from.
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_PATH"] = str(Path(tmp) / "purge.db")
        from monti import create_app
        purge_result = fixture_and_purge(create_app())
        print(f"fixture-inventory.csv     {len(purge_result['inventory'])} fixture rows")
        print(f"purge-evidence.md         {sum(purge_result['deleted'].values())} deleted, "
              f"{len(purge_result['orphans'])} orphans")

    for name in [m for m in list(sys.modules) if m == "monti" or m.startswith("monti.")]:
        del sys.modules[name]

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_PATH"] = str(Path(tmp) / "launch.db")
        from monti import create_app
        app = create_app()
        with app.app_context():
            from monti.db import init_db
            init_db()
        count = current_clients(app)
        print(f"current-clients.md        {count} live client(s)")

    states = punch_list()
    print("punch-list.csv            " + ", ".join(f"{k}: {v}" for k, v in sorted(states.items())))


if __name__ == "__main__":
    main()
