"""Revenue analytics for the admin portal.

Money books on the day funds are **confirmed**, not the day the order is placed —
an ACH debit still settling is not revenue yet. Every figure below reads from
`orders.funds_confirmed_at`, so the dashboard and the review gate never disagree.
"""
from datetime import timedelta

from .db import query
from .utils import parse, utcnow

PERIODS = [
    ("1d", 1, "1D"), ("7d", 7, "7D"), ("21d", 21, "21D"), ("45d", 45, "45D"),
    ("90d", 90, "90D"), ("180d", 180, "180D"), ("365d", 365, "365D"),
]
PERIOD_DAYS = {key: days for key, days, _ in PERIODS}


def _window(days, offset=0):
    """(start, end) for a window `days` long, shifted back by `offset` windows."""
    end = utcnow() - timedelta(days=days * offset)
    return (end - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _totals(days, offset=0):
    start, end = _window(days, offset)
    row = query(
        "SELECT COALESCE(SUM(total_cents), 0) AS revenue, COUNT(*) AS orders "
        "FROM orders WHERE payment_status = 'PAID' AND funds_confirmed_at >= ? "
        "AND funds_confirmed_at < ?", (start, end), one=True)
    return {"revenue": row["revenue"], "orders": row["orders"]}


def summary(period="7d"):
    days = PERIOD_DAYS.get(period, 7)
    cur, prev = _totals(days), _totals(days, offset=1)
    aov = round(cur["revenue"] / cur["orders"]) if cur["orders"] else 0

    def delta(now, before):
        return (now - before) / before if before else None

    return {
        "period": period, "days": days,
        "revenue": cur["revenue"], "orders": cur["orders"], "aov": aov,
        "revenue_delta": delta(cur["revenue"], prev["revenue"]),
        "orders_delta": delta(cur["orders"], prev["orders"]),
        "daily_average": round(cur["revenue"] / days) if days else 0,
        "prev_revenue": prev["revenue"],
    }


def series(period="7d"):
    """One point per day (or per hour for 1D), oldest first — ready to plot."""
    days = PERIOD_DAYS.get(period, 7)
    start, end = _window(days)
    if days == 1:
        rows = query(
            "SELECT strftime('%H', funds_confirmed_at) AS bucket, "
            "COALESCE(SUM(total_cents), 0) AS revenue, COUNT(*) AS orders FROM orders "
            "WHERE payment_status = 'PAID' AND funds_confirmed_at >= ? AND funds_confirmed_at < ? "
            "GROUP BY bucket", (start, end))
        found = {r["bucket"]: r for r in rows}
        out = []
        for h in range(24):
            key = f"{h:02d}"
            r = found.get(key)
            label = f"{(h % 12) or 12}{'am' if h < 12 else 'pm'}"
            out.append({"label": label, "full": f"Today, {label}",
                        "revenue": r["revenue"] if r else 0, "orders": r["orders"] if r else 0})
        return {"mode": "bar", "points": out}

    rows = query(
        "SELECT date(funds_confirmed_at) AS bucket, COALESCE(SUM(total_cents), 0) AS revenue, "
        "COUNT(*) AS orders FROM orders WHERE payment_status = 'PAID' "
        "AND funds_confirmed_at >= ? AND funds_confirmed_at < ? GROUP BY bucket", (start, end))
    found = {r["bucket"]: r for r in rows}
    out, day = [], parse(start)
    for _ in range(days):
        key = day.strftime("%Y-%m-%d")
        r = found.get(key)
        out.append({"label": day.strftime("%b %-d"), "full": day.strftime("%b %-d, %Y"),
                    "revenue": r["revenue"] if r else 0, "orders": r["orders"] if r else 0})
        day += timedelta(days=1)
    return {"mode": "bar" if days <= 21 else "area", "points": out}


def by_customer(period="7d", limit=10):
    days = PERIOD_DAYS.get(period, 7)
    start, end = _window(days)
    return query(
        "SELECT c.id, c.ref, c.company_name, COUNT(o.id) AS orders, "
        "COALESCE(SUM(o.total_cents), 0) AS revenue FROM customers c "
        "JOIN orders o ON o.customer_id = c.id AND o.payment_status = 'PAID' "
        "AND o.funds_confirmed_at >= ? AND o.funds_confirmed_at < ? "
        "GROUP BY c.id ORDER BY revenue DESC LIMIT ?", (start, end, limit))
