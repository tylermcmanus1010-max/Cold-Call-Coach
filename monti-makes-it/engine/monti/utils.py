"""Shared helpers: money, time, SLA math, formatting."""
from datetime import datetime, timedelta, timezone

FMT = "%Y-%m-%d %H:%M:%S"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now_str() -> str:
    return utcnow().strftime(FMT)


def parse(ts) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts
    ts = str(ts).replace("T", " ")
    for f in (FMT, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts[: len(f) + 2].strip(), f)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(ts))
    except ValueError:
        return None


def plus_hours(hours: int, base: datetime | None = None) -> str:
    return ((base or utcnow()) + timedelta(hours=hours)).strftime(FMT)


def money(cents) -> str:
    cents = int(cents or 0)
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def to_cents(value) -> int:
    """Accepts '1,299.50' / '1299.5' / 1299.5 and returns integer cents."""
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(round(float(value) * 100))
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        return int(round(float(cleaned) * 100))
    except ValueError:
        return 0


def to_int(value, default=0) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def countdown(deadline) -> dict:
    """Time remaining until a deadline, shaped for the UI."""
    dt = parse(deadline)
    if not dt:
        return {"text": "—", "overdue": False, "urgent": False, "hours": None}
    delta = dt - utcnow()
    total_minutes = int(delta.total_seconds() // 60)
    overdue = total_minutes < 0
    minutes = abs(total_minutes)
    h, m = divmod(minutes, 60)
    if h >= 24:
        d, rh = divmod(h, 24)
        text = f"{d}d {rh}h"
    elif h:
        text = f"{h}h {m}m"
    else:
        text = f"{m}m"
    return {
        "text": ("overdue by " + text) if overdue else (text + " left"),
        "short": text,
        "overdue": overdue,
        "urgent": (not overdue) and h < 6,
        "hours": round(delta.total_seconds() / 3600, 2),
    }


def pretty_dt(ts, with_time: bool = True) -> str:
    dt = parse(ts)
    if not dt:
        return "—"
    return dt.strftime("%b %-d, %Y · %H:%M") if with_time else dt.strftime("%b %-d, %Y")


def relative(ts) -> str:
    dt = parse(ts)
    if not dt:
        return "—"
    secs = (utcnow() - dt).total_seconds()
    past = secs >= 0
    secs = abs(secs)
    for limit, div, label in ((60, 1, "s"), (3600, 60, "m"), (86400, 3600, "h"), (2592000, 86400, "d")):
        if secs < limit:
            v = int(secs // div) or 1
            return f"{v}{label} ago" if past else f"in {v}{label}"
    return dt.strftime("%b %-d, %Y")


def initials(name: str) -> str:
    parts = [p for p in (name or "").replace("-", " ").split() if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def slugify(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in str(text))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


QUOTE_STATUS = {
    "NEW": ("Needs review", "amber"),
    "IN_REVIEW": ("Pricing", "blue"),
    "REJECTED": ("We declined", "red"),
    "ESTIMATE_SENT": ("Estimate sent", "violet"),
    "ACCEPTED": ("Accepted", "green"),
    "DECLINED": ("Declined", "slate"),
    "EXPIRED": ("Expired", "slate"),
}

ORDER_STATUS = {
    "PENDING_PAYMENT": ("Awaiting payment", "amber"),
    "PAYMENT_PROCESSING": ("Payment processing", "blue"),
    "IN_REVIEW": ("Manufacturer review", "violet"),
    "APPROVED": ("Approved", "green"),
    "IN_PRODUCTION": ("In production", "blue"),
    "SHIPPED": ("Shipped", "green"),
    "DELIVERED": ("Delivered", "green"),
    "ON_HOLD": ("On hold", "red"),
    "CANCELLED": ("Cancelled", "slate"),
    "REFUNDED": ("Refunded", "slate"),
}

CUSTOMER_STAGE = {
    "LEAD": ("Lead", "slate"),
    "QUOTING": ("Quoting", "amber"),
    "NEGOTIATING": ("Negotiating", "violet"),
    "ACTIVE": ("Active", "green"),
    "DORMANT": ("Dormant", "slate"),
    "LOST": ("Lost", "red"),
}


def status_label(value: str, table: str = "quote") -> tuple:
    source = {"quote": QUOTE_STATUS, "order": ORDER_STATUS, "customer": CUSTOMER_STAGE}[table]
    return source.get(value, (value.replace("_", " ").title() if value else "—", "slate"))
