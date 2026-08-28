"""A32–A36 — the transaction ledger.

Five checks over one record, and the reason there are five is that the ledger
fails in five unrelated ways:

    A32  a money event that produced no row, two rows, or the wrong status
    A33  two period views disagreeing about the same range
    A34  a member seeing someone else's row, or their own total disagreeing
         with the admin's total for them
    A35  an export that is not the screen it claims to be
    A36  a search that misses a match or invents one

A33 and A34 are the two worth reading closely.

A33 asserts roll-up, not just internal consistency. Checking that each view's
buckets sum to its own grand total, and that every row lands in exactly one
bucket, sounds like enough and is not: all of that stays true when the quarter
view buckets by a clock a second off from the month view's — same rows, still
one bucket each, still the same grand total, just filed under the wrong quarter.
The property §11.5.1 actually means is that the finer grouping composes into the
coarser one, so the check adds up the months inside each quarter and the
quarters inside each year and compares. That is what caught the skewed boundary
its own proof introduces.

A34 asserts agreement, not just isolation. Tenancy alone would pass if the
client ledger were empty. The check that matters is that the client's own total
equals the admin master ledger filtered to that customer — §11.6 names that
disagreement the single most damaging inconsistency this product could ship.
"""
import csv
import io

from . import Check, Finding


def _seed_money(ctx):
    """A known set of money events with deliberate boundary cases.

    Built rather than borrowed: the checks assert exact totals, so they need a
    row set whose arithmetic is known in advance. Returns the receipts written
    so the caller can clean up.
    """
    from monti import ledger

    written = []
    with ctx.app.app_context():
        order = ctx.query("SELECT * FROM orders WHERE customer_id = ? LIMIT 1",
                          (ctx.member_customer_id,))
        if not order:
            oid = ctx.execute(
                "INSERT INTO orders (ref, customer_id, status, payment_status, "
                "total_cents) VALUES ('MMI-O-LED1', ?, 'IN_REVIEW', 'PAID', 50000)",
                (ctx.member_customer_id,))
            order = ctx.query("SELECT * FROM orders WHERE id = ?", (oid,))
        order = order[0]

        # A transaction at the exact first instant of a month, quarter and year
        # — the case where inclusive/exclusive boundary handling either works or
        # quietly puts one row in two buckets.
        for when, cents in (("2026-01-01 00:00:00", 10000),   # year+quarter+month start
                            ("2026-04-01 00:00:00", 20000),   # quarter start
                            ("2026-03-31 23:59:59", 30000),   # last instant before it
                            ("2026-07-15 12:00:00", 40000)):
            written.append(ledger.charge(order, "CARD", cents, settled=True,
                                         occurred_at=when))
        # And one ACH debit in flight, which must not appear in any revenue total.
        written.append(ledger.charge(order, "ACH", 99999, settled=False,
                                     occurred_at="2026-07-16 12:00:00"))
    return written


def _clear(ctx, ids):
    for entry_id in ids:
        ctx.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))


# --------------------------------------------------------------------------
# A32 — completeness and reconciliation
# --------------------------------------------------------------------------
def run_a32(ctx):
    from monti import ledger

    findings = []
    with ctx.app.app_context():
        rows = ctx.query("SELECT COUNT(*) AS c FROM ledger_entries")
        if not rows[0]["c"]:
            return [Finding("A32", "the ledger is empty — an unexercised ledger check "
                                   "is not a pass")]

        # Exactly one charge row per order that has one at all.
        for row in ctx.query(
                "SELECT order_ref, COUNT(*) AS n FROM ledger_entries "
                "WHERE kind = 'CHARGE' AND order_ref IS NOT NULL "
                "GROUP BY order_ref HAVING n > 1"):
            findings.append(Finding(
                f"order {row['order_ref']}",
                f"{row['n']} charge rows for one order — a money event wrote twice"))

        # Every paid order has one.
        for row in ctx.query(
                "SELECT o.ref FROM orders o WHERE o.payment_status = 'PAID' "
                "AND NOT EXISTS (SELECT 1 FROM ledger_entries l WHERE l.order_id = o.id "
                "AND l.kind IN ('CHARGE','MANUAL_CONFIRMATION'))"):
            findings.append(Finding(
                f"order {row['ref']}", "paid, but wrote no ledger row"))

        # §11.4.3 — a pending row is never in a revenue total.
        pending = ctx.query(
            "SELECT COALESCE(SUM(gross_cents),0) AS c FROM ledger_entries "
            "WHERE status = 'PENDING'")[0]["c"]
        if pending:
            grand = ledger.periods("year")["grand"]
            if grand["pending_cents"] != pending:
                findings.append(Finding(
                    "ledger.totals", "the pending total does not match the pending rows"))
            settled_only = ctx.query(
                "SELECT COALESCE(SUM(gross_cents),0) AS c FROM ledger_entries "
                "WHERE status = 'SETTLED' AND kind IN ('CHARGE','MANUAL_CONFIRMATION')")[0]["c"]
            if grand["gross_cents"] != settled_only:
                findings.append(Finding(
                    "ledger.totals",
                    f"revenue is {grand['gross_cents']} but settled rows sum to "
                    f"{settled_only} — an unsettled debit is being counted"))

        # A reversal must point at something.
        for row in ctx.query(
                "SELECT receipt_no FROM ledger_entries WHERE kind = 'REVERSAL' "
                "AND reverses_id IS NULL"):
            findings.append(Finding(
                f"receipt {row['receipt_no']}", "a reversal that reverses nothing"))

        for brk in ledger.reconcile(record=False)["breaks"]:
            findings.append(Finding("reconciliation", brk["name"]))
    return findings


def prove_a32(ctx):
    """Drop one money event's row, and double another. Both must be named."""
    caught = []
    with ctx.app.app_context():
        paid = ctx.query(
            "SELECT o.id, o.ref FROM orders o JOIN ledger_entries l ON l.order_id = o.id "
            "WHERE o.payment_status = 'PAID' AND l.kind = 'CHARGE' LIMIT 1")
    if not paid:
        return False, "no paid order with a ledger row to break"
    order_id, order_ref = paid[0]["id"], paid[0]["ref"]

    row = ctx.query("SELECT * FROM ledger_entries WHERE order_id = ? AND kind = 'CHARGE'",
                    (order_id,))[0]
    saved = dict(row)

    ctx.execute("DELETE FROM ledger_entries WHERE id = ?", (row["id"],))
    try:
        found = [f for f in run_a32(ctx) if order_ref in f.where or "no ledger row" in f.detail]
        caught.append(("a money event's row deleted", bool(found),
                       str(found[0]) if found else "MISSED"))
    finally:
        ctx.execute(
            "INSERT INTO ledger_entries (id, receipt_no, customer_id, order_id, order_ref, "
            "kind, status, method, gross_cents, fee_cents, net_cents, occurred_at, period_tz) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (saved["id"], saved["receipt_no"], saved["customer_id"], saved["order_id"],
             saved["order_ref"], saved["kind"], saved["status"], saved["method"],
             saved["gross_cents"], saved["fee_cents"], saved["net_cents"],
             saved["occurred_at"], saved["period_tz"]))

    # And the other direction: one payment recorded twice.
    with ctx.app.app_context():
        from monti import ledger
        dup = ctx.execute(
            "INSERT INTO ledger_entries (receipt_no, customer_id, order_id, order_ref, kind, "
            "status, method, gross_cents, fee_cents, net_cents, occurred_at, period_tz) "
            "VALUES ('MMI-R-DUP', ?, ?, ?, 'CHARGE', 'SETTLED', 'CARD', ?, 0, ?, ?, 'UTC')",
            (saved["customer_id"], saved["order_id"], saved["order_ref"],
             saved["gross_cents"], saved["gross_cents"], saved["occurred_at"]))
    try:
        found = [f for f in run_a32(ctx) if "wrote twice" in f.detail or "duplicate" in f.detail]
        caught.append(("one payment recorded twice", bool(found),
                       str(found[0]) if found else "MISSED"))
    finally:
        ctx.execute("DELETE FROM ledger_entries WHERE id = ?", (dup,))

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


# --------------------------------------------------------------------------
# A33 — period arithmetic
# --------------------------------------------------------------------------
def run_a33(ctx):
    from monti import ledger

    findings = []
    with ctx.app.app_context():
        views = {g: ledger.periods(g) for g in ("month", "quarter", "year")}

        # All three are groupings of one row set, so their bucket sums and their
        # grand totals must all be the same number.
        grands = {g: v["grand"]["gross_cents"] for g, v in views.items()}
        if len(set(grands.values())) > 1:
            findings.append(Finding(
                "ledger.periods", f"the three views disagree on the grand total: {grands}"))

        for g, view in views.items():
            bucket_sum = sum(p["totals"]["gross_cents"] for p in view["periods"])
            if bucket_sum != view["grand"]["gross_cents"]:
                findings.append(Finding(
                    f"ledger.periods({g})",
                    f"buckets sum to {bucket_sum} but the grand total is "
                    f"{view['grand']['gross_cents']}"))

            # Every row lands in exactly one bucket.
            counted = sum(p["totals"]["row_count"] for p in view["periods"])
            total_rows = ctx.query("SELECT COUNT(*) AS c FROM ledger_entries")[0]["c"]
            if counted != total_rows:
                findings.append(Finding(
                    f"ledger.periods({g})",
                    f"{counted} rows across buckets, {total_rows} rows in the ledger — "
                    f"a transaction is in two periods or none"))

        # The months inside a quarter must add up to that quarter, and the
        # quarters inside a year to that year.
        #
        # Without this, A33 only asserted that each view is internally
        # consistent — that its buckets sum to its own grand total and that
        # every row lands in exactly one bucket. Both stay true when the quarter
        # view buckets by a clock one second off from the month view's: the same
        # rows, still each in one bucket, still summing to the same grand total,
        # just filed under the wrong quarter. The proof that moved the quarter
        # boundary by a second sailed past all three assertions.
        #
        # Roll-up is the property §11.5.1 actually means by the views agreeing:
        # they are groupings of one row set, so the finer grouping must compose
        # into the coarser one.
        month_totals = {p["key"]: p["totals"]["gross_cents"] for p in views["month"]["periods"]}
        for coarser, of_month in (("quarter", lambda k: f"{k[:4]}-Q{(int(k[5:7]) - 1) // 3 + 1}"),
                                  ("year", lambda k: k[:4])):
            rolled = {}
            for month_key, cents in month_totals.items():
                rolled[of_month(month_key)] = rolled.get(of_month(month_key), 0) + cents
            for bucket in views[coarser]["periods"]:
                expected = rolled.get(bucket["key"], 0)
                if bucket["totals"]["gross_cents"] != expected:
                    findings.append(Finding(
                        f"ledger.periods({coarser}) {bucket['key']}",
                        f"holds {bucket['totals']['gross_cents']} but the months inside it "
                        f"sum to {expected} — the two views bucket by different clocks"))
            unexpected = set(rolled) - {b["key"] for b in views[coarser]["periods"]}
            if unexpected:
                findings.append(Finding(
                    f"ledger.periods({coarser})",
                    f"the month view implies {sorted(unexpected)}, which the "
                    f"{coarser} view does not have"))

        # The boundary itself: a range ending at a period start must exclude a
        # transaction stamped at that instant, and the next range must include
        # it. Inclusive start, exclusive end (§11.5.1).
        boundary = "2026-04-01 00:00:00"
        before = ledger.periods("month", end=boundary)["grand"]["row_count"]
        after = ledger.periods("month", start=boundary)["grand"]["row_count"]
        everything = ledger.periods("month")["grand"]["row_count"]
        if before + after != everything:
            findings.append(Finding(
                "ledger.periods boundary",
                f"{before} before + {after} from {boundary} = {before + after}, "
                f"but the ledger holds {everything} — the boundary double-counts or drops"))
    return findings


def prove_a33(ctx):
    """Skew one period boundary by a second and confirm the check names it."""
    from monti import ledger

    original = ledger.period_key
    caught = []

    def skewed(ts, granularity):
        # The classic off-by-one: bucket the quarter view by a clock one second
        # ahead, so a transaction at a boundary lands in a different quarter
        # from the month it is in.
        if granularity == "quarter":
            from datetime import datetime, timedelta
            dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=-1)
            return f"{dt.year:04d}-Q{(dt.month - 1) // 3 + 1}"
        return original(ts, granularity)

    ledger.period_key = skewed
    try:
        findings = run_a33(ctx)
        caught.append(("the quarter boundary moved by one second", bool(findings),
                       str(findings[0]) if findings else "MISSED"))
    finally:
        ledger.period_key = original

    # And a view that drops a bucket entirely.
    original_periods = ledger.periods

    def lossy(granularity, **kw):
        view = original_periods(granularity, **kw)
        if granularity == "month" and len(view["periods"]) > 1:
            view["periods"] = view["periods"][:-1]
        return view

    ledger.periods = lossy
    try:
        findings = run_a33(ctx)
        hit = [f for f in findings if "buckets sum" in f.detail or "rows across buckets" in f.detail]
        caught.append(("a month bucket dropped from the view", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ledger.periods = original_periods

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


# --------------------------------------------------------------------------
# A34 — tenancy, and client-vs-admin agreement
# --------------------------------------------------------------------------
def run_a34(ctx):
    from monti import ledger

    findings = []
    with ctx.app.app_context():
        # The client ledger returns only the acting customer's rows.
        mine = ledger.search(customer_id=ctx.member_customer_id)["rows"]
        stray = [r for r in mine if r["customer_id"] != ctx.member_customer_id]
        if stray:
            findings.append(Finding(
                "ledger.search(client)",
                f"returned a row belonging to customer {stray[0]['customer_id']}"))

        # A client row carries no fee and no internal field.
        for row in mine[:50]:
            payload = ledger.client_row(row)
            leaked = set(payload) - ledger.CLIENT_FIELDS
            if leaked:
                findings.append(Finding(
                    f"receipt {row['receipt_no']}",
                    f"client payload carries {sorted(leaked)}"))
            for banned in ("fee_cents", "net_cents", "confirmed_by", "reverses_id"):
                if banned in payload:
                    findings.append(Finding(
                        f"receipt {row['receipt_no']}",
                        f"client payload exposes {banned!r}"))

        # The check that actually matters: the client's own totals equal the
        # admin master ledger filtered to that customer.
        client_total = ledger.client_totals(ctx.member_customer_id)
        admin_filtered = ledger.totals(
            ledger.search(customer_id=ctx.member_customer_id)["rows"])
        for field in ("gross_cents", "refunded_cents", "orders"):
            if client_total[field] != admin_filtered[field]:
                findings.append(Finding(
                    "client vs admin",
                    f"{field}: client says {client_total[field]}, admin filtered to "
                    f"this customer says {admin_filtered[field]}"))

        # And a cross-tenant receipt fetch resolves to nothing.
        other = ctx.query(
            "SELECT receipt_no FROM ledger_entries WHERE customer_id <> ? LIMIT 1",
            (ctx.member_customer_id,))
        if other:
            reached = ledger.receipt(other[0]["receipt_no"],
                                     customer_id=ctx.member_customer_id)
            if reached is not None:
                findings.append(Finding(
                    f"receipt {other[0]['receipt_no']}",
                    "another member's receipt was reachable by number"))

    # Through the route, as a member.
    if other:
        r = ctx.member_client.get(f"/portal/ledger/receipt/{other[0]['receipt_no']}")
        if r.status_code != 404:
            findings.append(Finding(
                f"/portal/ledger/receipt/{other[0]['receipt_no']}",
                f"returned {r.status_code}, expected 404"))
    return findings


def prove_a34(ctx):
    """Drop the client scope, and leak a fee into the client payload."""
    from monti import ledger

    caught = []
    original_search = ledger.search

    def unscoped(customer_id=None, **kw):
        return original_search(**kw)          # the scope silently ignored

    ledger.search = unscoped
    try:
        findings = run_a34(ctx)
        caught.append(("the client scope dropped from the ledger query", bool(findings),
                       str(findings[0]) if findings else "MISSED"))
    finally:
        ledger.search = original_search

    original_row = ledger.client_row

    def leaky(row):
        payload = original_row(row)
        payload["fee_cents"] = row["fee_cents"]   # our cut, on their page
        return payload

    ledger.client_row = leaky
    try:
        findings = run_a34(ctx)
        hit = [f for f in findings if "fee_cents" in f.detail]
        caught.append(("our fee added to the client payload", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ledger.client_row = original_row

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


# --------------------------------------------------------------------------
# A35 — export fidelity
# --------------------------------------------------------------------------
def _parse_csv(body):
    reader = csv.reader(io.StringIO(body))
    rows = list(reader)
    return rows[0], rows[1:]


def run_a35(ctx):
    from monti import ledger

    findings = []
    with ctx.app.app_context():
        found = ledger.search()
        columns, exported = ledger.to_export(found["rows"], client=False)

    if columns != ledger.ADMIN_COLUMNS:
        findings.append(Finding("ledger.to_export",
                                f"admin export columns are {columns}, expected "
                                f"{ledger.ADMIN_COLUMNS}"))
    if len(exported) != len(found["rows"]):
        findings.append(Finding(
            "ledger.to_export",
            f"exported {len(exported)} rows for {len(found['rows'])} on screen"))

    # Same rows, same order, through the actual route.
    header, body_rows = _parse_csv(
        ctx.admin_client.get("/admin/ledger/export.csv").get_data(as_text=True))
    if header != ledger.ADMIN_COLUMNS:
        findings.append(Finding("/admin/ledger/export.csv",
                                f"header is {header}, expected {ledger.ADMIN_COLUMNS}"))
    if len(body_rows) != len(found["rows"]):
        findings.append(Finding(
            "/admin/ledger/export.csv",
            f"{len(body_rows)} rows exported, {len(found['rows'])} shown on screen"))
    else:
        for i, (csv_row, screen_row) in enumerate(zip(body_rows, found["rows"])):
            if csv_row[0] != screen_row["receipt_no"]:
                findings.append(Finding(
                    f"/admin/ledger/export.csv row {i}",
                    f"export has {csv_row[0]}, the screen has {screen_row['receipt_no']} "
                    f"— the export is in a different order"))
                break

    # The client export carries no internal column.
    client_header, _ = _parse_csv(
        ctx.member_client.get("/portal/ledger/export.csv").get_data(as_text=True))
    for banned in ("fee_cents", "net_cents", "company_name"):
        if banned in client_header:
            findings.append(Finding("/portal/ledger/export.csv",
                                    f"client export contains {banned!r}"))
    return findings


def prove_a35(ctx):
    """Add a column the screen does not show, and drop a row from the export."""
    from monti import ledger

    caught = []
    original = ledger.to_export

    def extra_column(rows, client=False):
        columns, out = original(rows, client=client)
        columns = columns + ["internal_margin_cents"]
        for row in out:
            row["internal_margin_cents"] = 0
        return columns, out

    ledger.to_export = extra_column
    try:
        findings = run_a35(ctx)
        caught.append(("a column added to the export", bool(findings),
                       str(findings[0]) if findings else "MISSED"))
    finally:
        ledger.to_export = original

    def short(rows, client=False):
        columns, out = original(rows, client=client)
        return columns, out[:-1] if out else out

    ledger.to_export = short
    try:
        findings = run_a35(ctx)
        hit = [f for f in findings if "rows" in f.detail]
        caught.append(("a row dropped from the export", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ledger.to_export = original

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


# --------------------------------------------------------------------------
# A36 — search completeness
# --------------------------------------------------------------------------
def run_a36(ctx):
    from monti import ledger

    findings = []
    planted = _seed_money(ctx)
    try:
        with ctx.app.app_context():
            everything = ledger.search()["rows"]

            # Date range: the union of two adjacent half-open ranges is the whole.
            split = "2026-04-01 00:00:00"
            before = ledger.search(end=split)["rows"]
            after = ledger.search(start=split)["rows"]
            if len(before) + len(after) != len(everything):
                findings.append(Finding(
                    "ledger.search(date)",
                    f"{len(before)} + {len(after)} != {len(everything)} — the range "
                    f"boundary drops or double-counts a row"))

            # Member: every returned row belongs to a matching member, and every
            # matching member's row is returned.
            customer = ctx.query("SELECT * FROM customers WHERE id = ?",
                                 (ctx.member_customer_id,))[0]
            by_member = ledger.search(member=customer["company_name"])["rows"]
            expected = [r for r in everything if r["customer_id"] == customer["id"]]
            if len(by_member) != len(expected):
                findings.append(Finding(
                    "ledger.search(member)",
                    f"returned {len(by_member)} rows for {customer['company_name']}, "
                    f"{len(expected)} exist"))

            # Order reference: the complete chain, and nothing from another order.
            ref_row = next((r for r in everything if r["order_ref"]), None)
            if ref_row:
                chain = ledger.search(order_ref=ref_row["order_ref"])["rows"]
                expected_chain = [r for r in everything
                                  if (r["order_ref"] or "") == ref_row["order_ref"]]
                if len(chain) != len(expected_chain):
                    findings.append(Finding(
                        "ledger.search(order)",
                        f"returned {len(chain)} rows for {ref_row['order_ref']}, "
                        f"{len(expected_chain)} exist"))

            # Receipt: exactly one.
            hit = ledger.search(receipt_no=everything[0]["receipt_no"])["rows"]
            if len(hit) != 1:
                findings.append(Finding(
                    "ledger.search(receipt)",
                    f"a receipt number matched {len(hit)} rows"))

            # A search that caps says so.
            found = ledger.search()
            if found["matched"] > found["cap"] and not found["truncated"]:
                findings.append(Finding(
                    "ledger.search",
                    "more matches than the cap, but truncation was not reported"))
    finally:
        _clear(ctx, planted)
    return findings


def prove_a36(ctx):
    """Make one search mode miss rows, and another over-return."""
    from monti import ledger

    caught = []
    original = ledger.search

    def lossy(**kw):
        out = original(**kw)
        if kw.get("member"):
            out["rows"] = out["rows"][:-1] if out["rows"] else out["rows"]
        return out

    ledger.search = lossy
    try:
        findings = run_a36(ctx)
        hit = [f for f in findings if "member" in f.where]
        caught.append(("member search dropping a match", bool(hit),
                       str(hit[0]) if hit else "MISSED"))
    finally:
        ledger.search = original

    def silent_cap(**kw):
        out = original(**kw)
        out["truncated"] = False              # cap applied, never mentioned
        out["rows"] = out["rows"][:5]
        return out

    ledger.search = silent_cap
    try:
        findings = run_a36(ctx)
        caught.append(("a search truncating silently", bool(findings),
                       str(findings[0]) if findings else "MISSED"))
    finally:
        ledger.search = original

    missed = [n for n, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [
    Check("A32", "Ledger completeness and reconciliation", run_a32, prove_a32),
    Check("A33", "Period arithmetic: three views, one total, clean boundaries",
          run_a33, prove_a33),
    Check("A34", "Ledger tenancy, and client totals equal to the admin's for them",
          run_a34, prove_a34),
    Check("A35", "Export fidelity: the export is the screen", run_a35, prove_a35),
    Check("A36", "Search completeness across all four modes", run_a36, prove_a36),
]
