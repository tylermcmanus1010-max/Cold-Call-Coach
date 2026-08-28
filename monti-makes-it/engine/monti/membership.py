"""Membership — who gets to buy, and how much they can ask for.

Two ideas live here:

  Acceptance.  Anyone can request a quote. Only an accepted member can check out.
               Applications are screened, interviewed over video, and decided by a
               person — `APPROVED` is the only state that unlocks payment.

  The cycle.   Every member may open a limited number of NEW quotes per rolling
               window (10 in 30 days by default). Loyal accounts get theirs raised
               per-account; nothing here is global.
"""
from flask import current_app

from . import mail
from .auth import ensure_portal_user
from .db import execute, next_ref, query
from .utils import now_str, parse, pretty_dt, utcnow

# customers.membership_status
PROSPECT, APPLIED, INTERVIEW, MEMBER, DECLINED, PAUSED = (
    "PROSPECT", "APPLIED", "INTERVIEW", "MEMBER", "DECLINED", "PAUSED")

MEMBERSHIP_LABEL = {
    PROSPECT:  ("Not a member", "slate"),
    APPLIED:   ("Application in review", "amber"),
    INTERVIEW: ("Interview scheduled", "violet"),
    MEMBER:    ("Member", "green"),
    DECLINED:  ("Declined", "red"),
    PAUSED:    ("Paused", "slate"),
}

APPLICATION_LABEL = {
    "SUBMITTED":          ("New application", "amber"),
    "SCREENING":          ("Screening", "blue"),
    "INTERVIEW_SCHEDULED":("Interview booked", "violet"),
    "APPROVED":           ("Accepted", "green"),
    "DECLINED":           ("Declined", "slate"),
    "WAITLISTED":         ("Waitlisted", "slate"),
}

DEFAULT_QUOTE_LIMIT = 10
DEFAULT_CYCLE_DAYS = 30


def is_member(customer) -> bool:
    return bool(customer) and customer["membership_status"] == MEMBER


def _col(row, name, default=None):
    """Tolerate rows read before a migration has run."""
    try:
        value = row[name]
    except (IndexError, KeyError):
        return default
    return default if value is None else value


# --------------------------------------------------------------------------
# the quote cycle
# --------------------------------------------------------------------------
def quota_state(customer) -> dict:
    """How many new quotes this account may still open in the current window."""
    limit = int(_col(customer, "quote_limit", DEFAULT_QUOTE_LIMIT))
    days = int(_col(customer, "quote_cycle_days", DEFAULT_CYCLE_DAYS))
    used_rows = query(
        "SELECT created_at FROM quotes WHERE customer_id = ? "
        "AND created_at >= datetime('now', ?) ORDER BY created_at",
        (customer["id"], f"-{days} days"))
    used = len(used_rows)
    oldest = parse(used_rows[0]["created_at"]) if used_rows else None
    resets_at = None
    if oldest and used >= limit:
        from datetime import timedelta
        resets_at = (oldest + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "limit": limit,
        "days": days,
        "used": used,
        "remaining": max(0, limit - used),
        "exhausted": used >= limit,
        "resets_at": resets_at,
    }


def check_quota(customer):
    """Returns None if a new quote is allowed, or a message explaining why not."""
    if customer is None:
        return None
    state = quota_state(customer)
    if not state["exhausted"]:
        return None
    when = pretty_dt(state["resets_at"]) if state["resets_at"] else "your next cycle"
    return (
        f"You've used all {state['limit']} quote requests in your {state['days']}-day cycle. "
        f"The next slot opens {when}. If you need more, email "
        f"{current_app.config['SUPPORT_EMAIL']} — we raise the limit for accounts we work with often."
    )


def raise_limit(customer_id, new_limit, note, actor):
    execute("UPDATE customers SET quote_limit = ?, membership_note = ?, updated_at = ? WHERE id = ?",
            (int(new_limit), note, now_str(), customer_id))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
            (customer_id, f"Quote cycle limit set to {new_limit}" + (f" — {note}" if note else ""), actor))


# --------------------------------------------------------------------------
# applications
# --------------------------------------------------------------------------
def create_application(form) -> tuple:
    """Create the application and link (or create) a customer record. Returns (app, customer)."""
    email = form["email"].strip().lower()
    customer = query("SELECT * FROM customers WHERE lower(email) = ?", (email,), one=True)
    if customer is None:
        cust_ref = next_ref("MMI-C", "customers", start=1001)
        cid = execute(
            "INSERT INTO customers (ref, company_name, contact_name, email, phone, website, "
            "country, stage, source, membership_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'LEAD', 'WEBSITE', ?)",
            (cust_ref, form["company_name"].strip(), form["contact_name"].strip(), email,
             form.get("phone"), form.get("website"), form.get("country"), APPLIED))
        customer = query("SELECT * FROM customers WHERE id = ?", (cid,), one=True)
    elif customer["membership_status"] != MEMBER:
        execute("UPDATE customers SET membership_status = ?, updated_at = ? WHERE id = ?",
                (APPLIED, now_str(), customer["id"]))

    ref = next_ref("MMI-A", "applications", start=1001)
    app_id = execute(
        "INSERT INTO applications (ref, customer_id, company_name, contact_name, email, phone, "
        "website, country, business_type, years_trading, what_they_sell, categories, annual_volume, "
        "current_manufacturer, why, goals, availability, referral) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ref, customer["id"], form["company_name"].strip(), form["contact_name"].strip(), email,
         form.get("phone"), form.get("website"), form.get("country"), form.get("business_type"),
         form.get("years_trading"), form.get("what_they_sell"), form.get("categories"),
         form.get("annual_volume"), form.get("current_manufacturer"), form.get("why"),
         form.get("goals"), form.get("availability"), form.get("referral")))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, 'website')",
            (customer["id"], f"Submitted membership application {ref}"))
    application = query("SELECT * FROM applications WHERE id = ?", (app_id,), one=True)
    _notify_new_application(application, customer)
    return application, customer


def _notify_new_application(application, customer):
    cfg = current_app.config
    mail.send(application["email"], "We've received your application",
              template="application_received", application=application, customer=customer,
              company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"])
    mail.send(cfg["APPLICATIONS_EMAIL"],
              f"[APPLICATION {application['ref']}] {application['company_name']}",
              template="application_internal", application=application, customer=customer,
              company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"], pretty_dt=pretty_dt)


def schedule_interview(app_id, when, link, actor, note=None):
    execute(
        "UPDATE applications SET status = 'INTERVIEW_SCHEDULED', interview_at = ?, interview_link = ?, "
        "reviewer = ?, review_notes = COALESCE(?, review_notes), updated_at = ? WHERE id = ?",
        (when, link, actor, note, now_str(), app_id))
    application = query("SELECT * FROM applications WHERE id = ?", (app_id,), one=True)
    execute("UPDATE customers SET membership_status = ?, updated_at = ? WHERE id = ?",
            (INTERVIEW, now_str(), application["customer_id"]))
    execute(
        "INSERT INTO calendar_events (title, customer_id, kind, starts_at, location, notes, created_by) "
        "VALUES (?, ?, 'INTERVIEW', ?, ?, ?, ?)",
        (f"Membership interview · {application['company_name']}", application["customer_id"],
         when, link or "Zoom", f"Application {application['ref']}", actor))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'MEETING', ?, ?)",
            (application["customer_id"],
             f"Membership interview booked for {pretty_dt(when)}", actor))
    cfg = current_app.config
    mail.send(application["email"], "Your Monti membership interview",
              template="application_interview", application=application,
              company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"], pretty_dt=pretty_dt)
    return application


def approve_application(app_id, actor, quote_limit=DEFAULT_QUOTE_LIMIT, note=None):
    """Accept the applicant: they become a member and get portal credentials."""
    application = query("SELECT * FROM applications WHERE id = ?", (app_id,), one=True)
    execute(
        "UPDATE applications SET status = 'APPROVED', decided_at = ?, reviewer = ?, "
        "decision_reason = COALESCE(?, decision_reason), updated_at = ? WHERE id = ?",
        (now_str(), actor, note, now_str(), app_id))
    execute(
        "UPDATE customers SET membership_status = ?, member_since = ?, stage = 'ACTIVE', "
        "quote_limit = ?, updated_at = ? WHERE id = ?",
        (MEMBER, now_str(), int(quote_limit), now_str(), application["customer_id"]))
    customer = query("SELECT * FROM customers WHERE id = ?", (application["customer_id"],), one=True)
    _, password = ensure_portal_user(customer, name=application["contact_name"])
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
            (customer["id"], f"Accepted as a member — {application['ref']}", actor))
    cfg = current_app.config
    mail.send(customer["email"], f"You're in — welcome to {cfg['COMPANY_NAME']}",
              template="application_approved", application=application, customer=customer,
              password=password, company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"],
              quote_limit=int(quote_limit))
    return customer, password


def decline_application(app_id, actor, reason, waitlist=False):
    status = "WAITLISTED" if waitlist else "DECLINED"
    execute(
        "UPDATE applications SET status = ?, decided_at = ?, reviewer = ?, decision_reason = ?, "
        "updated_at = ? WHERE id = ?", (status, now_str(), actor, reason, now_str(), app_id))
    application = query("SELECT * FROM applications WHERE id = ?", (app_id,), one=True)
    execute("UPDATE customers SET membership_status = ?, updated_at = ? WHERE id = ?",
            (PROSPECT if waitlist else DECLINED, now_str(), application["customer_id"]))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
            (application["customer_id"],
             f"Application {application['ref']} {'waitlisted' if waitlist else 'declined'}"
             + (f" — {reason}" if reason else ""), actor))
    cfg = current_app.config
    mail.send(application["email"],
              "About your Monti membership application",
              template="application_declined", application=application, waitlist=waitlist,
              reason=reason, company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"])
    return application
