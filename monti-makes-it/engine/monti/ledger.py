"""The transaction ledger — the financial record of the business (§11.4).

Not a report generated from the order log on demand, and not a convenience
view. An append-only record with one immutable row per money event; the admin
master view, the client view, the three period reports and the exports are all
projections of it.

Three rules govern it, and each one is enforced here rather than remembered:

  Derived, never typed.   Every writer in this module is a named money event —
                          `charge`, `settle`, `refund`, `reverse`, `fee`. There
                          is no `create_entry(**fields)` and no update path that
                          takes arbitrary columns, so there is no route through
                          which a person or an agent writes a row by hand. A
                          correction is `reverse()`, which writes a new row
                          pointing at the old one.

  It must reconcile.      `reconcile()` compares the ledger to the order log
                          line for line and names what disagrees. It cannot fix
                          anything: it has no write path to `ledger_entries`.
                          §11.4 forbids closing a break by adjusting the ledger,
                          and the way to make that stick is to give the
                          reconciler nothing to adjust with.

  Revenue means settled.  `PENDING` is a real state, not a label. Every revenue
                          aggregate in this module filters on `status =
                          'SETTLED'`, and an ACH debit in flight transitions in
                          place rather than spawning a second row — settlement
                          is an UPDATE of `status`, which is the one mutation
                          the append-only rule permits, because the alternative
                          is two rows for one payment and a ledger that
                          double-counts every bank transfer.

Periods are the other place this gets subtle. §11.5.1 requires that the month,
quarter and year views agree on the same range, which only holds if they bucket
by the same clock — so `PERIOD_TZ` is stored on every row and every view derives
its buckets from `occurred_at` interpreted in it. Boundaries are inclusive start,
exclusive end, everywhere.
"""
import json
from datetime import datetime, timezone

from .db import execute, query

# One timezone for the whole ledger (§11.5.1). Stored per row so a later change
# is visible in the data rather than silently re-bucketing history.
PERIOD_TZ = "UTC"

KINDS = ("CHARGE", "SETTLEMENT", "REFUND", "PARTIAL_REFUND", "REVERSAL",
         "MANUAL_CONFIRMATION", "FEE")
STATUSES = ("PENDING", "SETTLED", "FAILED")

# Rows that count toward revenue. §11.4.3: an ACH debit in flight is not
# revenue, and a fee is our cost rather than the customer's payment.
REVENUE_KINDS = ("CHARGE", "MANUAL_CONFIRMATION")
REFUND_KINDS = ("REFUND", "PARTIAL_REFUND", "REVERSAL")

# What a client may see. §11.6: never our fees, margin, cost build-up, or any
# internal reconciliation state. Enforced as an allowlist for the same reason
# the public catalogue uses one — a denylist passes the day a column is added.
CLIENT_FIELDS = frozenset({
    "receipt_no", "occurred_at", "kind", "status", "method",
    "gross_cents", "order_ref", "note",
})


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def next_receipt_no():
    """Sequential, human-quotable, and unique.

    Derived from the highest existing number rather than from a row count: a
    count reuses a number after a delete, and a receipt number that has ever
    pointed at two different transactions is worse than no receipt number.
    """
    row = query("SELECT receipt_no FROM ledger_entries ORDER BY id DESC LIMIT 1", one=True)
    if row is None:
        return "MMI-R-100001"
    return f"MMI-R-{int(row['receipt_no'].rsplit('-', 1)[1]) + 1}"


# --------------------------------------------------------------------------
# the writers — one per money event, and nothing else writes
# --------------------------------------------------------------------------
def _write(customer_id, kind, status, *, order=None, method=None, gross_cents=0,
           fee_cents=0, occurred_at=None, reverses_id=None, confirmed_by=None,
           review_outcome=None, note=None):
    """The single INSERT. Private on purpose: callers use the event functions."""
    if kind not in KINDS:
        raise ValueError(f"unknown ledger kind: {kind!r}")
    if status not in STATUSES:
        raise ValueError(f"unknown ledger status: {status!r}")
    receipt = next_receipt_no()
    entry_id = execute(
        "INSERT INTO ledger_entries (receipt_no, customer_id, order_id, order_ref, kind, "
        "status, method, gross_cents, fee_cents, net_cents, occurred_at, period_tz, "
        "reverses_id, confirmed_by, review_outcome, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (receipt, customer_id,
         order["id"] if order else None,
         order["ref"] if order else None,
         kind, status, method, gross_cents, fee_cents, gross_cents - fee_cents,
         occurred_at or _now(), PERIOD_TZ, reverses_id, confirmed_by,
         review_outcome, note))
    return entry_id


def entry_for_order(order_id, kind):
    """The existing row of this kind for this order, if there is one.

    Used by the order lifecycle to stay idempotent: a replayed webhook must not
    turn one payment into two ledger rows, and asking first is cheaper than
    unpicking a double count afterwards.
    """
    return query(
        "SELECT * FROM ledger_entries WHERE order_id = ? AND kind = ? ORDER BY id LIMIT 1",
        (order_id, kind), one=True)


def charge(order, method, gross_cents, settled, occurred_at=None):
    """A card capture or an ACH initiation. §11.7.

    `settled` decides the status and nothing else: a card capture lands SETTLED,
    an ACH debit lands PENDING and stays out of revenue until `settle()` moves
    it. One row either way — the pending row is the same row that later settles.
    """
    return _write(order["customer_id"], "CHARGE",
                  "SETTLED" if settled else "PENDING",
                  order=order, method=method, gross_cents=gross_cents,
                  occurred_at=occurred_at)


def settle(order_id, occurred_at=None):
    """An ACH debit landing. Transitions the pending row; never adds one.

    The only mutation the append-only rule allows, and it is confined to
    `status` and the settlement time. Writing a second row here would
    double-count every bank transfer in the ledger.
    """
    row = query(
        "SELECT * FROM ledger_entries WHERE order_id = ? AND kind = 'CHARGE' "
        "AND status = 'PENDING' ORDER BY id LIMIT 1", (order_id,), one=True)
    if row is None:
        return None
    execute("UPDATE ledger_entries SET status = 'SETTLED', occurred_at = ? WHERE id = ?",
            (occurred_at or row["occurred_at"], row["id"]))
    return row["id"]


def fail(order_id, note=None):
    """An ACH debit bouncing. The pending row becomes FAILED, still one row."""
    row = query(
        "SELECT * FROM ledger_entries WHERE order_id = ? AND kind = 'CHARGE' "
        "AND status = 'PENDING' ORDER BY id LIMIT 1", (order_id,), one=True)
    if row is None:
        return None
    execute("UPDATE ledger_entries SET status = 'FAILED', note = ? WHERE id = ?",
            (note, row["id"]))
    return row["id"]


def manual_confirmation(order, method, gross_cents, confirmed_by, occurred_at=None):
    """A wire or PO confirmed by a person. Settled, and the person is named."""
    return _write(order["customer_id"], "MANUAL_CONFIRMATION", "SETTLED",
                  order=order, method=method, gross_cents=gross_cents,
                  confirmed_by=confirmed_by, occurred_at=occurred_at)


def fee(order, fee_cents, method, occurred_at=None):
    """The provider's cut. Its own row, linked to the transaction, admin-only."""
    return _write(order["customer_id"], "FEE", "SETTLED", order=order,
                  method=method, gross_cents=0, fee_cents=fee_cents,
                  occurred_at=occurred_at)


def refund(order, gross_cents, partial=False, note=None, occurred_at=None):
    """Money going back. A new linked row, never an edit to the original."""
    original = query(
        "SELECT id FROM ledger_entries WHERE order_id = ? AND kind = 'CHARGE' "
        "ORDER BY id LIMIT 1", (order["id"],), one=True)
    return _write(order["customer_id"],
                  "PARTIAL_REFUND" if partial else "REFUND", "SETTLED",
                  order=order, gross_cents=-abs(gross_cents),
                  reverses_id=original["id"] if original else None,
                  note=note, occurred_at=occurred_at)


def reverse(entry_id, note, occurred_at=None):
    """A correction. §11.4.1: never a mutation — a new row pointing at the old."""
    original = query("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,), one=True)
    if original is None:
        raise ValueError(f"no ledger entry {entry_id} to reverse")
    order = query("SELECT * FROM orders WHERE id = ?", (original["order_id"],), one=True)
    return _write(original["customer_id"], "REVERSAL", "SETTLED", order=order,
                  method=original["method"], gross_cents=-original["gross_cents"],
                  fee_cents=-original["fee_cents"], reverses_id=entry_id,
                  note=note, occurred_at=occurred_at)


# --------------------------------------------------------------------------
# periods (§11.5.1)
# --------------------------------------------------------------------------
def _parse(ts):
    return datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")


def period_key(ts, granularity):
    """Which month, quarter or year a timestamp falls in.

    All three read the same `occurred_at` in the same stored timezone, which is
    what makes §11.5.1's "all three views sum to the same total" hold: they are
    different groupings of one set of rows, not three independent calculations.
    """
    dt = _parse(ts)
    if granularity == "month":
        return f"{dt.year:04d}-{dt.month:02d}"
    if granularity == "quarter":
        return f"{dt.year:04d}-Q{(dt.month - 1) // 3 + 1}"
    if granularity == "year":
        return f"{dt.year:04d}"
    raise ValueError(f"unknown granularity: {granularity!r}")


def period_label(key, granularity):
    if granularity == "month":
        year, month = key.split("-")
        return datetime(int(year), int(month), 1).strftime("%B %Y")
    return key


def _rows_in_range(customer_id=None, start=None, end=None):
    """Rows in [start, end) — inclusive start, exclusive end, everywhere.

    Half-open is not a stylistic choice: a transaction stamped exactly midnight
    on the first of a month has to land in one period and only one, and the only
    way inclusive-inclusive achieves that is by everyone remembering to subtract
    a second somewhere. A33 asserts the boundary case directly.
    """
    sql = "SELECT * FROM ledger_entries WHERE 1=1"
    args = []
    if customer_id is not None:
        sql += " AND customer_id = ?"
        args.append(customer_id)
    if start:
        sql += " AND occurred_at >= ?"
        args.append(start)
    if end:
        sql += " AND occurred_at < ?"
        args.append(end)
    return query(sql + " ORDER BY occurred_at, id", tuple(args))


def totals(rows):
    """The measures every period view reports, over whatever rows it was given."""
    settled = [r for r in rows if r["status"] == "SETTLED"]
    revenue = sum(r["gross_cents"] for r in settled if r["kind"] in REVENUE_KINDS)
    refunded = -sum(r["gross_cents"] for r in settled if r["kind"] in REFUND_KINDS)
    fees = sum(r["fee_cents"] for r in settled)
    orders = len({r["order_id"] for r in settled
                  if r["kind"] in REVENUE_KINDS and r["order_id"]})
    pending = sum(r["gross_cents"] for r in rows if r["status"] == "PENDING")
    return {
        "gross_cents": revenue,
        "refunded_cents": refunded,
        "net_cents": revenue - refunded - fees,
        "fees_cents": fees,
        "orders": orders,
        "aov_cents": (revenue // orders) if orders else 0,
        "refund_rate": (refunded / revenue) if revenue else 0.0,
        "pending_cents": pending,
        "row_count": len(rows),
    }


def periods(granularity, customer_id=None, start=None, end=None):
    """One bucket per period, newest first, each with its own totals and delta.

    The grand total is computed from the same row list the buckets are built
    from, so `sum(bucket) == grand` is arithmetic rather than a coincidence —
    which is the property A33 exists to hold on to.
    """
    rows = _rows_in_range(customer_id, start, end)
    buckets = {}
    for row in rows:
        buckets.setdefault(period_key(row["occurred_at"], granularity), []).append(row)

    ordered = sorted(buckets)
    out = []
    for i, key in enumerate(ordered):
        current = totals(buckets[key])
        previous = totals(buckets[ordered[i - 1]]) if i else None
        out.append({
            "key": key,
            "label": period_label(key, granularity),
            "totals": current,
            "previous": previous,
            "delta": _delta(current, previous),
        })
    out.reverse()
    return {"granularity": granularity, "periods": out, "grand": totals(rows)}


def _delta(current, previous):
    """Period-over-period movement, as a fraction. None when there is no prior."""
    if not previous:
        return None
    out = {}
    for field in ("gross_cents", "net_cents", "orders", "aov_cents"):
        was, now = previous[field], current[field]
        out[field] = ((now - was) / was) if was else None
    return out


# --------------------------------------------------------------------------
# search (§11.5.2)
# --------------------------------------------------------------------------
SEARCH_CAP = 500


def search(customer_id=None, start=None, end=None, member=None,
           order_ref=None, receipt_no=None):
    """The four modes, combinable. Returns rows plus whether it was truncated.

    §11.5.2: a search that silently truncates is a P1, so the cap is reported
    rather than applied quietly — the caller gets `truncated` and `matched` and
    can offer the export instead of pretending the page is the whole answer.
    """
    sql = ("SELECT l.*, c.company_name FROM ledger_entries l "
           "JOIN customers c ON c.id = l.customer_id WHERE 1=1")
    args = []
    if customer_id is not None:
        sql += " AND l.customer_id = ?"
        args.append(customer_id)
    if start:
        sql += " AND l.occurred_at >= ?"
        args.append(start)
    if end:
        sql += " AND l.occurred_at < ?"
        args.append(end)
    if member:
        # Member search is by company, contact or reference — the three things
        # an admin actually has in front of them when a client calls.
        sql += (" AND (lower(c.company_name) LIKE ? OR lower(COALESCE(c.contact_name,'')) LIKE ?"
                " OR lower(c.ref) LIKE ?)")
        needle = f"%{member.lower()}%"
        args += [needle, needle, needle]
    if order_ref:
        sql += " AND lower(COALESCE(l.order_ref,'')) = ?"
        args.append(order_ref.lower())
    if receipt_no:
        sql += " AND lower(l.receipt_no) = ?"
        args.append(receipt_no.lower())

    rows = query(sql + " ORDER BY l.occurred_at DESC, l.id DESC", tuple(args))
    return {
        "rows": rows[:SEARCH_CAP],
        "matched": len(rows),
        "truncated": len(rows) > SEARCH_CAP,
        "cap": SEARCH_CAP,
    }


def order_chain(order_ref):
    """One order's full transaction chain, in sequence. §11.5.2's order search."""
    return query(
        "SELECT * FROM ledger_entries WHERE lower(COALESCE(order_ref,'')) = ? "
        "ORDER BY occurred_at, id", (order_ref.lower(),))


def receipt(receipt_no, customer_id=None):
    """One receipt. `customer_id` scopes it, so the client route cannot fetch
    another member's by number — the tenancy is in the query, not in a check
    the caller might forget."""
    sql = ("SELECT l.*, c.company_name, c.ref AS customer_ref "
           "FROM ledger_entries l JOIN customers c ON c.id = l.customer_id "
           "WHERE lower(l.receipt_no) = ?")
    args = [receipt_no.lower()]
    if customer_id is not None:
        sql += " AND l.customer_id = ?"
        args.append(customer_id)
    return query(sql, tuple(args), one=True)


# --------------------------------------------------------------------------
# export (§11.5.1) and the client projection (§11.6)
# --------------------------------------------------------------------------
ADMIN_COLUMNS = ["receipt_no", "occurred_at", "company_name", "order_ref", "kind",
                 "status", "method", "gross_cents", "fee_cents", "net_cents"]
CLIENT_COLUMNS = ["receipt_no", "occurred_at", "order_ref", "kind", "status",
                  "method", "gross_cents"]


def to_export(rows, client=False):
    """The export is the on-screen view: same rows, same columns, same order.

    Built from the same row list the screen renders and from a fixed column
    list, so `A35` can assert equality rather than similarity. The client
    column list is a strict subset that omits every fee and internal field.
    """
    columns = CLIENT_COLUMNS if client else ADMIN_COLUMNS
    out = []
    for row in rows:
        keys = row.keys()
        out.append({c: (row[c] if c in keys else None) for c in columns})
    return columns, out


def client_row(row):
    """One ledger row as its owner sees it. Allowlisted, per §11.6."""
    keys = row.keys()
    return {f: (row[f] if f in keys else None) for f in sorted(CLIENT_FIELDS)}


def client_totals(customer_id, start=None, end=None):
    """A member's totals. Identical arithmetic to the admin view filtered to
    them, because it is literally the same function over the same rows — which
    is what makes A34's "the two ledgers agree" true by construction rather
    than by two implementations happening to match."""
    return totals(_rows_in_range(customer_id, start, end))


# --------------------------------------------------------------------------
# reconciliation (§11.4.2)
# --------------------------------------------------------------------------
def reconcile(record=True):
    """Compare the ledger to the order log and name what disagrees.

    Deliberately has no write path to `ledger_entries`. §11.4.2 forbids closing
    a break by adjusting the ledger, and the reliable way to enforce that is to
    give the reconciler no means to do it: it can only write a
    `reconciliation_runs` row describing what it found.
    """
    breaks = []

    ledger_settled = query(
        "SELECT COALESCE(SUM(gross_cents), 0) AS c FROM ledger_entries "
        "WHERE status = 'SETTLED' AND kind IN ('CHARGE', 'MANUAL_CONFIRMATION')",
        one=True)["c"]
    order_paid = query(
        "SELECT COALESCE(SUM(total_cents), 0) AS c FROM orders WHERE payment_status = 'PAID'",
        one=True)["c"]

    # A paid order with no settled ledger row is money we took and did not
    # record — the break that matters most.
    for row in query(
            "SELECT o.id, o.ref, o.total_cents FROM orders o WHERE o.payment_status = 'PAID' "
            "AND NOT EXISTS (SELECT 1 FROM ledger_entries l WHERE l.order_id = o.id "
            "                AND l.status = 'SETTLED' AND l.kind IN ('CHARGE','MANUAL_CONFIRMATION'))"):
        breaks.append({
            "name": "paid order with no settled ledger row",
            "order_ref": row["ref"], "order_cents": row["total_cents"],
        })

    # And the mirror: a settled row against an order the order log does not
    # consider paid.
    for row in query(
            "SELECT l.receipt_no, l.order_ref, l.gross_cents FROM ledger_entries l "
            "LEFT JOIN orders o ON o.id = l.order_id "
            "WHERE l.status = 'SETTLED' AND l.kind IN ('CHARGE','MANUAL_CONFIRMATION') "
            "AND (o.id IS NULL OR o.payment_status <> 'PAID')"):
        breaks.append({
            "name": "settled ledger row with no paid order",
            "receipt_no": row["receipt_no"], "order_ref": row["order_ref"],
            "ledger_cents": row["gross_cents"],
        })

    # Two settled charge rows for one order is a double count.
    for row in query(
            "SELECT order_ref, COUNT(*) AS n FROM ledger_entries "
            "WHERE kind = 'CHARGE' AND order_ref IS NOT NULL "
            "GROUP BY order_ref HAVING n > 1"):
        breaks.append({"name": "duplicate charge rows for one order",
                       "order_ref": row["order_ref"], "count": row["n"]})

    if ledger_settled != order_paid:
        breaks.append({"name": "ledger total does not equal order-log total",
                       "ledger_cents": ledger_settled, "order_log_cents": order_paid})

    result = {"ledger_cents": ledger_settled, "order_log_cents": order_paid,
              "provider_cents": None, "breaks": breaks, "break_count": len(breaks)}

    if record:
        execute(
            "INSERT INTO reconciliation_runs (ledger_cents, order_log_cents, "
            "provider_cents, break_count, breaks) VALUES (?, ?, ?, ?, ?)",
            (ledger_settled, order_paid, None, len(breaks), json.dumps(breaks)))
    return result


def backfill_from_orders():
    """Write ledger rows for orders that predate the ledger.

    The ledger arrived after the order log, so without this every historic paid
    order is a reconciliation break on the first run — and a ledger that opens
    with breaks it cannot explain teaches everyone to ignore breaks. Idempotent:
    an order that already has a charge row is skipped.
    """
    written = 0
    for order in query("SELECT * FROM orders WHERE payment_status IN ('PAID', 'PROCESSING')"):
        if query("SELECT id FROM ledger_entries WHERE order_id = ? AND kind = 'CHARGE'",
                 (order["id"],), one=True):
            continue
        paid = order["payment_status"] == "PAID"
        charge(order, order["payment_method"] or "CARD", order["total_cents"],
               settled=paid, occurred_at=order["funds_confirmed_at"] or order["created_at"])
        if paid and order["processing_fee_cents"]:
            fee(order, order["processing_fee_cents"], order["payment_method"] or "CARD",
                occurred_at=order["funds_confirmed_at"] or order["created_at"])
        written += 1
    return written
