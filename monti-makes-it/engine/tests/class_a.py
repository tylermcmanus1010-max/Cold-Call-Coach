"""The Class A gate.

    python tests/class_a.py            run every check against the current build
    python tests/class_a.py --prove    break each check on purpose, prove it fails
    python tests/class_a.py --all      both, and write the evidence artifacts

The second mode is the one that matters. §0.2.7: a check that has never failed
is not a check, and §1.6 makes counting an unproven check toward coverage a P0
in its own right. So coverage here is not "checks that exist" — it is checks
whose proof ran and caught the defect it introduced. A check that passes but
cannot prove itself is reported as UNPROVEN and does not count.

The proofs edit source files and revert them. That is deliberate — §2.4 asks for
a demonstration against a realistic deliberate defect, and commenting out a real
guard is the realistic defect. Every proof restores the file in a `finally`, and
the runner verifies the tree is unchanged before it reports.
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))

os.environ.setdefault("SECRET_KEY", "class-a-checks")

from checks import collect                                        # noqa: E402


class Context:
    """Everything the checks share: an app, three clients, and a live database.

    Built on a copy of the launch database rather than the developer's, so a
    check that writes a probe row cannot damage real data and so two runs of the
    suite start from the same place.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="monti-classa-")
        self.db_path = str(Path(self.tmpdir) / "checks.db")
        self.company_name = None
        self._build()

    # -- lifecycle ---------------------------------------------------------
    def _build(self):
        os.environ["DATABASE_PATH"] = self.db_path
        from monti import create_app
        self.app = create_app()
        self.app.config.update(DATABASE_PATH=self.db_path, TESTING=True,
                               # Proofs edit templates on disk. Jinja caches
                               # compiled templates and Flask leaves auto-reload
                               # off outside debug, so without this a proof's
                               # edit is invisible unless something else
                               # rebuilt the app first — which made two proofs
                               # order-dependent rather than deterministic.
                               TEMPLATES_AUTO_RELOAD=True)
        self.app.jinja_env.auto_reload = True
        self.company_name = self.app.config["COMPANY_NAME"]

        with self.app.app_context():
            from monti.db import init_db
            init_db()
            self._ensure_data()

        self.public_client = self.app.test_client()
        self.admin_client = self.app.test_client()
        self.member_client = self.app.test_client()
        self._sign_in()

    def reload(self):
        """Re-import the package after a proof has edited a source file.

        Flask views and modules are captured at import, so editing a file on
        disk changes nothing until the module tree is dropped and rebuilt.
        Without this, every proof would report MISSED and the whole coverage
        number would be a lie in the flattering direction.
        """
        for name in [m for m in sys.modules if m == "monti" or m.startswith("monti.")]:
            del sys.modules[name]
        self._build()

    def close(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- fixtures for the probes -------------------------------------------
    def _ensure_data(self):
        """Launch data, plus a second member so tenancy has something to probe.

        The second member is created here rather than by `flask launch` because
        it exists only to be the customer the first one must not reach.

        Probe rows are not stamped as fixtures. They are scaffolding for a
        throwaway database, and stamping them would make A14 fail on the
        harness's own furniture rather than on anything the purge missed — which
        is a check reporting a defect that does not exist, and just as useless as
        one that misses a defect that does.
        """
        from monti.agents import provision_agent
        from monti.auth import create_user
        from monti.db import execute, query
        from monti.launch import provision_boars_head

        if not query("SELECT id FROM users WHERE role = 'ADMIN'", one=True):
            create_user("checks-admin@montimakesit.com", "checks-admin-pw",
                        name="Checks Admin", role="ADMIN")

        boars_head_id = provision_boars_head()
        boars_head = query("SELECT * FROM customers WHERE id = ?", (boars_head_id,), one=True)
        if not query("SELECT id FROM users WHERE customer_id = ?", (boars_head_id,), one=True):
            create_user(boars_head["email"], "checks-member-pw", name="Boars Head",
                        role="CLIENT", customer_id=boars_head_id)

        other = query("SELECT * FROM customers WHERE ref = 'MMI-C-9001'", one=True)
        if other is None:
            other_id = execute(
                "INSERT INTO customers (ref, company_name, email, membership_status, "
                "is_fixture) VALUES ('MMI-C-9001', 'Probe Counterparty', "
                "'probe@example.invalid', 'MEMBER', 0)")
            provision_agent(other_id)
            # Rows for the first member to fail to reach.
            execute("INSERT INTO quotes (ref, customer_id, title, due_at) "
                    "VALUES ('MMI-Q-9001', ?, 'Probe quote', datetime('now', '+1 day'))",
                    (other_id,))
            execute("INSERT INTO orders (ref, customer_id, status) "
                    "VALUES ('MMI-O-9001', ?, 'PENDING_PAYMENT')", (other_id,))
        else:
            other_id = other["id"]

        # A public item registered to nobody. A07 needs something an ordering
        # attempt can legitimately be refused for; with every public item
        # registered to the probing member there is no refusal to observe, and a
        # check that cannot observe its subject must not report a pass.
        if not query("SELECT id FROM catalog_items WHERE sku = 'MMI-X-9001'", one=True):
            execute(
                "INSERT INTO catalog_items (sku, name, category, description, "
                "unit_price_cents, moq, lead_time_days, range_low_cents, range_high_cents, "
                "typical_moq, typical_lead_time_days, range_drivers, is_public, is_active, "
                "is_fixture) VALUES ('MMI-X-9001', 'Unregistered probe item', "
                "'Packaging & print', 'Public, and registered to nobody.', 0, 1000, 30, "
                "20, 40, 1000, 30, 'quantity and spec', 1, 1, 0)")

        # Money events for the ledger checks. The launch database is deliberately
        # empty of orders, so A32-A36 would have nothing to assert against —
        # and a ledger check with no ledger is not a pass, it is an unexercised
        # check. These are harness scaffolding, not fixtures (see above).
        from monti import ledger
        if not query("SELECT id FROM ledger_entries", one=True):
            for cid, ref, cents, when, settled in (
                    (boars_head_id, "MMI-O-L001", 250000, "2026-01-01 00:00:00", True),
                    (boars_head_id, "MMI-O-L002", 180000, "2026-03-31 23:59:59", True),
                    (boars_head_id, "MMI-O-L003", 90000, "2026-04-01 00:00:00", True),
                    (other_id,      "MMI-O-L004", 320000, "2026-07-01 09:00:00", True),
                    (boars_head_id, "MMI-O-L005", 47000, "2026-07-16 12:00:00", False)):
                oid = execute(
                    "INSERT INTO orders (ref, customer_id, status, payment_status, "
                    "payment_method, total_cents, funds_confirmed_at, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ref, cid, "IN_REVIEW" if settled else "PAYMENT_PROCESSING",
                     "PAID" if settled else "PROCESSING",
                     "CARD" if settled else "ACH", cents, when if settled else None, when))
                order = query("SELECT * FROM orders WHERE id = ?", (oid,), one=True)
                ledger.charge(order, "CARD" if settled else "ACH", cents,
                              settled=settled, occurred_at=when)

        self.member_customer_id = boars_head_id
        self.other_customer_id = other_id
        self.admin_email = "checks-admin@montimakesit.com"
        self.member_email = boars_head["email"]

    def _sign_in(self):
        """Sign both clients in, with a CSRF token minted the way a browser does.

        `check_csrf` is a before_request and is not relaxed under TESTING, which
        is the right posture for the app: a test suite that turns the protection
        off stops testing the thing that ships. So each client GETs the form
        first to get a token into its session, then posts with it.
        """
        for client, email, password in (
                (self.admin_client, self.admin_email, "checks-admin-pw"),
                (self.member_client, self.member_email, "checks-member-pw")):
            client.get("/login")
            r = client.post("/login", data={"email": email, "password": password,
                                            "_csrf": self.csrf(client)})
            if r.status_code not in (302, 303):
                raise RuntimeError(
                    f"the harness could not sign in as {email} (HTTP {r.status_code}); "
                    "every probe below would report a false pass")

    # -- helpers the checks call -------------------------------------------
    def query(self, sql, args=()):
        with self.app.app_context():
            from monti.db import query
            return query(sql, args)

    def execute(self, sql, args=()):
        with self.app.app_context():
            from monti.db import execute
            return execute(sql, args)

    def csrf(self, client):
        """This client's CSRF token, seeding one into the session if it has none.

        `login` calls `session.clear()`, which drops the token minted to render
        the login form, and not every authenticated page renders a form to mint
        a fresh one. Reading the empty value and posting with it made probe
        POSTs fail the CSRF check instead of reaching the guard they were aiming
        at — which looks exactly like a pass and is not one.

        Writing the token straight into the session is what the server's own
        `csrf_token()` does on first use, so this is the same act, not a bypass:
        the request still has to carry a token that matches the session, which
        is the property under test everywhere else.
        """
        with client.session_transaction() as sess:
            token = sess.get("_csrf")
            if not token:
                token = secrets.token_urlsafe(32)
                sess["_csrf"] = token
        return token

    def raw_sqlite(self):
        """A direct connection to the checks database, outside the app's plumbing.

        `get_db()` opens a connection per app context and sets `foreign_keys = ON`
        every time, so a pragma issued through `execute()` is undone before the
        next statement runs. A proof that needs to write a row the schema would
        reject — an orphan, which is exactly what A14 has to detect — needs one
        connection it controls for the whole operation.
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def first_id(self, table, customer_id):
        rows = self.query(f"SELECT id FROM {table} WHERE customer_id = ? LIMIT 1",
                          (customer_id,))
        return rows[0]["id"] if rows else None

    def first_file_id(self, customer_id):
        rows = self.query(
            "SELECT f.id FROM quote_files f JOIN quotes q ON q.id = f.quote_id "
            "WHERE q.customer_id = ? LIMIT 1", (customer_id,))
        return rows[0]["id"] if rows else None

    def make_order_for(self, customer_id, item_id):
        """An order carrying an item the customer is not registered for."""
        order_id = self.execute(
            "INSERT INTO orders (ref, customer_id, status, subtotal_cents, total_cents) "
            "VALUES (?, ?, 'PENDING_PAYMENT', 1000, 1000)",
            (f"MMI-O-P{customer_id}{item_id}", customer_id))
        item = self.query("SELECT * FROM catalog_items WHERE id = ?", (item_id,))[0]
        self.execute(
            "INSERT INTO order_items (order_id, catalog_item_id, name, sku, "
            "unit_price_cents, quantity, line_total_cents) VALUES (?, ?, ?, ?, 1, 1000, 1000)",
            (order_id, item_id, item["name"], item["sku"]))
        return order_id

    def make_paid_unreviewed_order(self):
        """Funds confirmed, review window open, nothing cleared."""
        return self.execute(
            "INSERT INTO orders (ref, customer_id, status, payment_status, "
            "funds_confirmed_at, review_release_at, subtotal_cents, total_cents) "
            "VALUES (?, ?, 'IN_REVIEW', 'PAID', datetime('now'), "
            "datetime('now', '+24 hours'), 1000, 1000)",
            (f"MMI-O-R{os.getpid()}", self.member_customer_id))

    # brand.py scans what the app renders, so it needs the route lists.
    @property
    def public_routes(self):
        routes = ["/", "/catalogue", "/how-it-works", "/membership", "/contact",
                  "/quote", "/apply", "/login"]
        for row in self.query("SELECT sku FROM catalog_items WHERE is_public = 1"):
            routes.append(f"/catalogue/{row['sku']}")
        return routes

    @property
    def member_routes(self):
        return ["/portal/", "/portal/quotes", "/portal/orders", "/portal/catalog",
                "/portal/purchases", "/portal/cart"]

    @property
    def admin_routes(self):
        return ["/admin/", "/admin/quotes", "/admin/orders", "/admin/crm",
                "/admin/catalog", "/admin/applications", "/admin/emails"]


def _tree_fingerprint():
    """A hash of every source file, so a proof that failed to revert is caught.

    The proofs deliberately edit the working tree. If one crashed between the
    edit and the restore, every later check would be running against broken
    source and the run would report nonsense. Comparing before and after turns
    that into a loud failure.
    """
    h = hashlib.sha256()
    for path in sorted((ENGINE / "monti").rglob("*.py")) + \
                sorted((ENGINE / "monti" / "templates").rglob("*.html")):
        h.update(path.read_bytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Class A checks and their proofs")
    parser.add_argument("--prove", action="store_true",
                        help="run each check's broken-input proof")
    parser.add_argument("--all", action="store_true", help="run both, and write evidence")
    parser.add_argument("--evidence", default="evidence",
                        help="where to write the evidence artifacts")
    args = parser.parse_args()

    run_checks = not args.prove or args.all
    run_proofs = args.prove or args.all

    before = _tree_fingerprint()
    ctx = Context()
    checks = collect()
    results = {}

    try:
        if run_checks:
            print("\n=== Class A checks ===")
            for check in checks:
                findings = check.run(ctx)
                results.setdefault(check.id, {})["title"] = check.title
                results[check.id]["findings"] = [str(f) for f in findings]
                status = "PASS" if not findings else f"FAIL ({len(findings)})"
                print(f"  [{status:>9}] {check.id}  {check.title}")
                for finding in findings[:6]:
                    print(f"              → {finding}")
                if len(findings) > 6:
                    print(f"              → …and {len(findings) - 6} more")

        if run_proofs:
            print("\n=== Broken-input proofs (§2.4) ===")
            for check in checks:
                try:
                    caught, detail = check.prove(ctx)
                except Exception as exc:                    # a proof that crashes is unproven
                    caught, detail = False, f"the proof raised {type(exc).__name__}: {exc}"
                results.setdefault(check.id, {})["title"] = check.title
                results[check.id]["proven"] = caught
                results[check.id]["proof"] = detail
                print(f"  [{'PROVEN' if caught else 'UNPROVEN':>9}] {check.id}  {detail}")

        after = _tree_fingerprint()
        if before != after:
            print("\n!! The source tree changed during the run — a proof did not revert. "
                  "Treat every result above as void and check `git status`.")
            return 2

        if args.all:
            out = Path(args.evidence)
            out.mkdir(parents=True, exist_ok=True)
            (out / "class-a-proofs.md").write_text(_proof_report(results))
            (out / "class-a-results.json").write_text(json.dumps(results, indent=2))
            print(f"\nEvidence written to {out}/")

        return _summarise(results, run_checks, run_proofs)
    finally:
        ctx.close()


def _summarise(results, ran_checks, ran_proofs):
    total = len(results)
    failing = [cid for cid, r in results.items() if r.get("findings")]
    unproven = [cid for cid, r in results.items()
                if ran_proofs and not r.get("proven")]

    print("\n" + "=" * 60)
    if ran_checks:
        print(f"  {total - len(failing)}/{total} checks pass")
    if ran_proofs:
        # Coverage counts a check only if its proof caught a real defect.
        print(f"  {total - len(unproven)}/{total} checks are proven able to fail")
        if unproven:
            print(f"  UNPROVEN, and therefore not counted: {', '.join(sorted(unproven))}")
    if failing:
        print(f"  FAILING: {', '.join(sorted(failing))}")
    print("=" * 60)
    return 1 if (failing or unproven) else 0


def _proof_report(results):
    lines = [
        "# Class A proofs",
        "",
        "One block per check. A check counts toward Class A coverage only when the",
        "defect its proof introduced was caught and named — §2.4, and §1.6's rule that",
        "counting an unproven check toward coverage is itself a P0.",
        "",
    ]
    for cid in sorted(results):
        r = results[cid]
        lines.append(f"## {cid} — {r.get('title', '')}")
        lines.append("")
        lines.append(f"- **Result on the current build:** "
                     f"{'pass' if not r.get('findings') else 'FAIL'}")
        if r.get("findings"):
            for f in r["findings"][:10]:
                lines.append(f"  - {f}")
        if "proven" in r:
            lines.append(f"- **Proof:** {'caught' if r['proven'] else 'DID NOT CATCH'}")
            lines.append(f"- **Defect introduced and reverted:** {r.get('proof', '')}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
