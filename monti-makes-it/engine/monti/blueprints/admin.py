"""Admin bay — the internal command center.

CRM, calendar, quote queue with the 24h SLA, private catalog with per-customer
assignment, the full order log, and the manufacturer review gate.
"""
import calendar as pycal
from datetime import date, datetime, timedelta

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    session, url_for,
)

from .. import analytics, catalog as catalog_mod, mail, membership
from .. import orders as orders_mod
from ..auth import admin_required, create_user, ensure_portal_user
from ..db import execute, next_ref, query
from ..utils import (money, now_str, parse, plus_hours, pretty_dt, to_cents,
                     to_int, utcnow)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@admin_required
def guard():
    """Every route in this blueprint requires ADMIN."""
    return None


@bp.app_context_processor
def inject_admin_counts():
    if g.get("user") and g.user["role"] == "ADMIN":
        return {
            "nav_quote_count": query(
                "SELECT COUNT(*) AS c FROM quotes WHERE status IN ('NEW','IN_REVIEW')",
                one=True)["c"],
            "nav_review_count": query(
                "SELECT COUNT(*) AS c FROM orders WHERE status = 'IN_REVIEW'", one=True)["c"],
            "nav_incoming_count": query(
                "SELECT COUNT(*) AS c FROM quotes WHERE status = 'NEW'", one=True)["c"],
            "nav_application_count": query(
                "SELECT COUNT(*) AS c FROM applications WHERE status IN "
                "('SUBMITTED','SCREENING','INTERVIEW_SCHEDULED')", one=True)["c"],
            "nav_clients": query(
                "SELECT id, company_name FROM customers WHERE membership_status = 'MEMBER' "
                "ORDER BY company_name LIMIT 8"),
            "membership_label": membership.MEMBERSHIP_LABEL,
            "application_label": membership.APPLICATION_LABEL,
        }
    return {}


# --------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------
@bp.route("/")
def dashboard():
    open_quotes = query(
        "SELECT q.*, c.company_name FROM quotes q JOIN customers c ON c.id = q.customer_id "
        "WHERE q.status IN ('NEW','IN_REVIEW') ORDER BY q.due_at ASC")
    review_orders = query(
        "SELECT o.*, c.company_name FROM orders o JOIN customers c ON c.id = o.customer_id "
        "WHERE o.status = 'IN_REVIEW' ORDER BY o.review_release_at ASC")
    recent_orders = query(
        "SELECT o.*, c.company_name FROM orders o JOIN customers c ON c.id = o.customer_id "
        "ORDER BY o.created_at DESC LIMIT 8")
    upcoming = query(
        "SELECT e.*, c.company_name FROM calendar_events e "
        "LEFT JOIN customers c ON c.id = e.customer_id "
        "WHERE e.starts_at >= ? AND e.done = 0 ORDER BY e.starts_at LIMIT 8", (now_str(),))
    open_applications = query(
        "SELECT * FROM applications WHERE status IN ('SUBMITTED','SCREENING','INTERVIEW_SCHEDULED') "
        "ORDER BY CASE status WHEN 'SUBMITTED' THEN 0 WHEN 'SCREENING' THEN 1 ELSE 2 END, created_at")
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d")
    stats = {
        "open_quotes": len(open_quotes),
        "overdue": sum(1 for q in open_quotes if parse(q["due_at"]) and parse(q["due_at"]) < utcnow()),
        "in_review": len(review_orders),
        "revenue_mtd": query(
            "SELECT COALESCE(SUM(total_cents),0) AS s FROM orders WHERE payment_status = 'PAID' "
            "AND funds_confirmed_at >= ?", (month_start,), one=True)["s"],
        "pipeline": query(
            "SELECT COALESCE(SUM(e.total_cents),0) AS s FROM estimates e JOIN quotes q ON q.id = e.quote_id "
            "WHERE q.status = 'ESTIMATE_SENT'", one=True)["s"],
        "customers": query("SELECT COUNT(*) AS c FROM customers", one=True)["c"],
        "members": query(
            "SELECT COUNT(*) AS c FROM customers WHERE membership_status = 'MEMBER'", one=True)["c"],
        "applications": len(open_applications),
        "active_customers": query(
            "SELECT COUNT(*) AS c FROM customers WHERE stage = 'ACTIVE'", one=True)["c"],
        "awaiting_payment": query(
            "SELECT COALESCE(SUM(total_cents),0) AS s FROM orders WHERE status = 'PENDING_PAYMENT'",
            one=True)["s"],
    }
    return render_template("admin/dashboard.html", open_quotes=open_quotes,
                           review_orders=review_orders, recent_orders=recent_orders,
                           upcoming=upcoming, stats=stats, applications=open_applications)


@bp.route("/clients/<int:customer_id>/open")
def open_client(customer_id):
    """Open a client's portal exactly as they see it. Clearly banner-marked."""
    customer = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    if customer is None:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.crm"))
    session["view_as"] = customer_id
    return redirect(url_for("portal.dashboard"))


@bp.route("/clients/close")
def close_client():
    session.pop("view_as", None)
    return redirect(request.referrer or url_for("admin.crm"))


@bp.route("/revenue")
def revenue():
    period = request.args.get("period", "7d")
    if period not in analytics.PERIOD_DAYS:
        period = "7d"
    return render_template(
        "admin/revenue.html", period=period, periods=analytics.PERIODS,
        summary=analytics.summary(period), series=analytics.series(period),
        by_customer=analytics.by_customer(period),
        clients=query("SELECT * FROM customers WHERE membership_status = 'MEMBER' "
                      "ORDER BY company_name"))


# --------------------------------------------------------------------------
# incoming quotes — triage before anything gets priced
# --------------------------------------------------------------------------
@bp.route("/incoming")
def incoming():
    """Everything that has just landed, oldest first, with the SLA clock running."""
    rows = query(
        "SELECT q.*, c.company_name, c.ref AS customer_ref, c.membership_status, "
        "c.lifetime_value_cents, (SELECT COUNT(*) FROM quotes q2 WHERE q2.customer_id = q.customer_id) "
        "AS customer_quotes FROM quotes q JOIN customers c ON c.id = q.customer_id "
        "WHERE q.status = 'NEW' ORDER BY q.due_at ASC")
    recent = query(
        "SELECT q.*, c.company_name FROM quotes q JOIN customers c ON c.id = q.customer_id "
        "WHERE q.triaged_at IS NOT NULL ORDER BY q.triaged_at DESC LIMIT 8")
    files = {}
    for r in rows:
        files[r["id"]] = query("SELECT * FROM quote_files WHERE quote_id = ?", (r["id"],))
    return render_template("admin/incoming.html", quotes=rows, files=files, recent=recent)


@bp.route("/incoming/<int:quote_id>/<action>", methods=("POST",))
def triage(quote_id, action):
    quote = query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True)
    if quote is None or quote["status"] != "NEW":
        flash("That request has already been dealt with.", "error")
        return redirect(url_for("admin.incoming"))
    customer = query("SELECT * FROM customers WHERE id = ?", (quote["customer_id"],), one=True)
    actor = g.user["name"] or g.user["email"]
    cfg = current_app.config

    if action == "accept":
        execute("UPDATE quotes SET status = 'IN_REVIEW', triaged_at = ?, triaged_by = ?, "
                "updated_at = ? WHERE id = ?", (now_str(), actor, now_str(), quote_id))
        execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                "VALUES (?, 'SYSTEM', ?, ?)",
                (customer["id"], f"Accepted {quote['ref']} for pricing", actor))
        mail.send(customer["email"], f"We're pricing {quote['ref']}",
                  template="quote_accepted", quote=quote, customer=customer,
                  company=cfg["COMPANY_NAME"], sla=cfg["QUOTE_SLA_HOURS"],
                  pretty_dt=pretty_dt, site_url=cfg["SITE_URL"])
        flash(f"{quote['ref']} accepted — it's in the pricing queue.", "ok")
        return redirect(url_for("admin.quote_detail", quote_id=quote_id))

    if action == "reject":
        reason = (request.form.get("reason") or "").strip()
        if not reason:
            flash("Give a reason — the client is sent it.", "error")
            return redirect(url_for("admin.incoming"))
        execute("UPDATE quotes SET status = 'REJECTED', decline_reason = ?, triaged_at = ?, "
                "triaged_by = ?, updated_at = ? WHERE id = ?",
                (reason, now_str(), actor, now_str(), quote_id))
        execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                "VALUES (?, 'SYSTEM', ?, ?)",
                (customer["id"], f"Declined to quote {quote['ref']} — {reason}", actor))
        mail.send(customer["email"], f"About your request {quote['ref']}",
                  template="quote_rejected", quote=quote, customer=customer, reason=reason,
                  company=cfg["COMPANY_NAME"], site_url=cfg["SITE_URL"])
        flash(f"{quote['ref']} declined and the client has been told why.", "ok")
        return redirect(url_for("admin.incoming"))

    flash("Unknown action.", "error")
    return redirect(url_for("admin.incoming"))


# --------------------------------------------------------------------------
# quote queue
# --------------------------------------------------------------------------
@bp.route("/quotes")
def quotes():
    status = request.args.get("status", "open")
    sql = ("SELECT q.*, c.company_name, c.ref AS customer_ref, "
           "(SELECT total_cents FROM estimates e WHERE e.quote_id = q.id ORDER BY e.id DESC LIMIT 1) AS est_total "
           "FROM quotes q JOIN customers c ON c.id = q.customer_id ")
    args = []
    if status == "open":
        sql += "WHERE q.status IN ('NEW','IN_REVIEW') "
    elif status == "pricing":
        sql += "WHERE q.status = 'IN_REVIEW' "
    elif status and status != "all":
        sql += "WHERE q.status = ? "
        args.append(status)
    sql += "ORDER BY CASE WHEN q.status IN ('NEW','IN_REVIEW') THEN 0 ELSE 1 END, q.due_at ASC, q.created_at DESC"
    return render_template("admin/quotes.html", quotes=query(sql, args), status=status)


@bp.route("/quotes/<int:quote_id>", methods=("GET", "POST"))
def quote_detail(quote_id):
    quote = query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True)
    if quote is None:
        flash("Quote not found.", "error")
        return redirect(url_for("admin.quotes"))
    customer = query("SELECT * FROM customers WHERE id = ?", (quote["customer_id"],), one=True)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "claim":
            execute("UPDATE quotes SET status = 'IN_REVIEW', updated_at = ? WHERE id = ?",
                    (now_str(), quote_id))
            flash("Marked as being priced.", "ok")
        elif action == "notes":
            execute("UPDATE quotes SET internal_notes = ?, updated_at = ? WHERE id = ?",
                    (request.form.get("internal_notes"), now_str(), quote_id))
            flash("Internal notes saved.", "ok")
        elif action == "estimate":
            return _save_estimate(quote, customer)
        elif action == "expire":
            execute("UPDATE quotes SET status = 'EXPIRED', updated_at = ? WHERE id = ?",
                    (now_str(), quote_id))
            flash("Quote closed as expired.", "ok")
        return redirect(url_for("admin.quote_detail", quote_id=quote_id))

    estimate = query("SELECT * FROM estimates WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
                     (quote_id,), one=True)
    files = query("SELECT * FROM quote_files WHERE quote_id = ? ORDER BY id", (quote_id,))
    history = query("SELECT * FROM estimates WHERE quote_id = ? ORDER BY created_at DESC", (quote_id,))
    order = query("SELECT * FROM orders WHERE source_quote_id = ? ORDER BY id DESC LIMIT 1",
                  (quote_id,), one=True)
    return render_template("admin/quote_detail.html", quote=quote, customer=customer,
                           estimate=estimate, files=files, history=history, order=order)


def _save_estimate(quote, customer):
    form = request.form
    unit = to_cents(form.get("unit_price"))
    qty = to_int(form.get("quantity"), quote["quantity"] or 1) or 1
    tooling = to_cents(form.get("tooling"))
    sample = to_cents(form.get("sample"))
    shipping = to_cents(form.get("shipping"))
    duties = to_cents(form.get("duties"))
    total = unit * qty + tooling + sample + shipping + duties

    estimate_id = execute(
        "INSERT INTO estimates (quote_id, unit_price_cents, moq, quantity, tooling_cents, "
        "sample_cents, shipping_cents, duties_cents, lead_time_days, ship_method, incoterm, "
        "valid_until, notes, total_cents, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (quote["id"], unit, to_int(form.get("moq"), 1), qty, tooling, sample, shipping, duties,
         to_int(form.get("lead_time_days"), 30), form.get("ship_method"),
         form.get("incoterm") or quote["incoterm"], form.get("valid_until"),
         form.get("notes"), total, g.user["email"]),
    )
    send_now = form.get("send") == "1"
    if send_now:
        execute("UPDATE quotes SET status = 'ESTIMATE_SENT', responded_at = ?, updated_at = ? WHERE id = ?",
                (now_str(), now_str(), quote["id"]))
        estimate = query("SELECT * FROM estimates WHERE id = ?", (estimate_id,), one=True)
        cfg = current_app.config
        mail.send(
            customer["email"], f"Your estimate is ready — {quote['ref']}",
            template="estimate_ready", quote=quote, customer=customer, estimate=estimate,
            company=cfg["COMPANY_NAME"], money=money, pretty_dt=pretty_dt, site_url=cfg["SITE_URL"],
        )
        execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'EMAIL', ?, ?)",
                (customer["id"], f"Sent estimate on {quote['ref']} — {money(total)}", g.user["email"]))
        flash(f"Estimate sent to {customer['email']}.", "ok")
    else:
        execute("UPDATE quotes SET status = 'IN_REVIEW', updated_at = ? WHERE id = ?",
                (now_str(), quote["id"]))
        flash("Estimate saved as a draft — not sent.", "ok")
    return redirect(url_for("admin.quote_detail", quote_id=quote["id"]))


@bp.route("/quotes/<int:quote_id>/to-catalog", methods=("POST",))
def quote_to_catalog(quote_id):
    """Turn a priced project into a private catalog item, assigned to that client."""
    quote = query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True)
    estimate = query("SELECT * FROM estimates WHERE quote_id = ? ORDER BY id DESC LIMIT 1",
                     (quote_id,), one=True)
    if quote is None or estimate is None:
        flash("Price the project before adding it to the catalog.", "error")
        return redirect(url_for("admin.quote_detail", quote_id=quote_id))
    sku = (request.form.get("sku") or f"MMI-{quote['ref'].split('-')[-1]}").strip().upper()
    if query("SELECT id FROM catalog_items WHERE sku = ?", (sku,), one=True):
        sku = f"{sku}-{quote['id']}"
    item_id = execute(
        "INSERT INTO catalog_items (sku, name, category, description, materials, specs, "
        "unit_price_cents, moq, lead_time_days, origin_quote_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sku, quote["title"], quote["category"], quote["description"], quote["materials"],
         "\n".join(filter(None, [quote["dimensions"], quote["color_finish"], quote["packaging"]])),
         estimate["unit_price_cents"], estimate["moq"], estimate["lead_time_days"], quote["id"]),
    )
    execute("INSERT OR IGNORE INTO catalog_assignments (item_id, customer_id, assigned_by) VALUES (?, ?, ?)",
            (item_id, quote["customer_id"], g.user["email"]))
    flash(f"Added to the catalog as {sku} and assigned to this client.", "ok")
    return redirect(url_for("admin.catalog_detail", item_id=item_id))


# --------------------------------------------------------------------------
# membership applications
# --------------------------------------------------------------------------
@bp.route("/applications")
def applications():
    status = request.args.get("status", "open")
    sql = ("SELECT a.*, c.membership_status, c.lifetime_value_cents FROM applications a "
           "LEFT JOIN customers c ON c.id = a.customer_id ")
    args = []
    if status == "open":
        sql += "WHERE a.status IN ('SUBMITTED','SCREENING','INTERVIEW_SCHEDULED') "
    elif status and status != "all":
        sql += "WHERE a.status = ? "
        args.append(status)
    sql += ("ORDER BY CASE a.status WHEN 'SUBMITTED' THEN 0 WHEN 'SCREENING' THEN 1 "
            "WHEN 'INTERVIEW_SCHEDULED' THEN 2 ELSE 3 END, a.created_at DESC")
    counts = {r["status"]: r["c"] for r in
              query("SELECT status, COUNT(*) AS c FROM applications GROUP BY status")}
    return render_template("admin/applications.html", applications=query(sql, args),
                           status=status, counts=counts)


@bp.route("/applications/<int:app_id>", methods=("GET", "POST"))
def application_detail(app_id):
    application = query("SELECT * FROM applications WHERE id = ?", (app_id,), one=True)
    if application is None:
        flash("Application not found.", "error")
        return redirect(url_for("admin.applications"))
    actor = g.user["name"] or g.user["email"]

    if request.method == "POST":
        action = request.form.get("action")
        if action == "screening":
            execute("UPDATE applications SET status = 'SCREENING', reviewer = ?, updated_at = ? "
                    "WHERE id = ?", (actor, now_str(), app_id))
            flash("Marked as under review.", "ok")
        elif action == "notes":
            execute("UPDATE applications SET review_notes = ?, updated_at = ? WHERE id = ?",
                    (request.form.get("review_notes"), now_str(), app_id))
            flash("Notes saved.", "ok")
        elif action == "interview":
            when = (request.form.get("interview_at") or "").replace("T", " ")
            if len(when) == 16:
                when += ":00"
            if not when:
                flash("Pick a date and time for the call.", "error")
            else:
                membership.schedule_interview(app_id, when, request.form.get("interview_link"),
                                              actor, request.form.get("review_notes"))
                flash("Interview booked, added to your calendar, and the applicant emailed.", "ok")
        elif action == "approve":
            customer, password = membership.approve_application(
                app_id, actor,
                quote_limit=to_int(request.form.get("quote_limit"),
                                   current_app.config["QUOTE_LIMIT"]),
                note=request.form.get("decision_reason"))
            if password:
                flash(f"Accepted. Portal login for {customer['email']} — "
                      f"temporary password: {password}", "ok")
            else:
                flash("Accepted. They already had portal credentials.", "ok")
        elif action in ("decline", "waitlist"):
            reason = (request.form.get("decision_reason") or "").strip()
            if not reason:
                flash("Give a reason — the applicant is told what it is.", "error")
            else:
                membership.decline_application(app_id, actor, reason,
                                               waitlist=(action == "waitlist"))
                flash("Decision recorded and the applicant has been emailed.", "ok")
        return redirect(url_for("admin.application_detail", app_id=app_id))

    customer = None
    quotes_rows = []
    if application["customer_id"]:
        customer = query("SELECT * FROM customers WHERE id = ?",
                         (application["customer_id"],), one=True)
        quotes_rows = query("SELECT * FROM quotes WHERE customer_id = ? ORDER BY created_at DESC",
                            (application["customer_id"],))
    return render_template("admin/application_detail.html", application=application,
                           customer=customer, quotes=quotes_rows,
                           default_link=current_app.config["INTERVIEW_LINK"],
                           default_limit=current_app.config["QUOTE_LIMIT"])


# --------------------------------------------------------------------------
# CRM
# --------------------------------------------------------------------------
@bp.route("/crm")
def crm():
    stage = request.args.get("stage", "")
    search = (request.args.get("q") or "").strip()
    sql = ("SELECT c.*, "
           "(SELECT COUNT(*) FROM quotes q WHERE q.customer_id = c.id AND "
           " q.created_at >= datetime('now', '-' || c.quote_cycle_days || ' days')) AS cycle_quotes, "
           "(SELECT COUNT(*) FROM quotes q WHERE q.customer_id = c.id) AS quote_count, "
           "(SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) AS order_count, "
           "(SELECT MAX(created_at) FROM crm_activities a WHERE a.customer_id = c.id) AS last_touch "
           "FROM customers c WHERE 1=1 ")
    args = []
    if stage:
        sql += "AND c.stage = ? "
        args.append(stage)
    member_filter = request.args.get("membership", "")
    if member_filter:
        sql += "AND c.membership_status = ? "
        args.append(member_filter)
    if search:
        sql += "AND (c.company_name LIKE ? OR c.contact_name LIKE ? OR c.email LIKE ? OR c.ref LIKE ?) "
        args += [f"%{search}%"] * 4
    sql += "ORDER BY c.lifetime_value_cents DESC, c.created_at DESC"
    customers = query(sql, args)
    stage_counts = {r["stage"]: r["c"] for r in
                    query("SELECT stage, COUNT(*) AS c FROM customers GROUP BY stage")}
    member_counts = {r["membership_status"]: r["c"] for r in
                     query("SELECT membership_status, COUNT(*) AS c FROM customers "
                           "GROUP BY membership_status")}
    return render_template("admin/crm.html", customers=customers, stage=stage,
                           search=search, stage_counts=stage_counts,
                           member_filter=member_filter, member_counts=member_counts,
                           total_ltv=sum(c["lifetime_value_cents"] for c in customers))


@bp.route("/crm/new", methods=("GET", "POST"))
def crm_new():
    if request.method == "POST":
        form = request.form
        if not form.get("company_name") or not form.get("email"):
            flash("Company name and email are required.", "error")
        else:
            ref = next_ref("MMI-C", "customers", start=1001)
            cid = execute(
                "INSERT INTO customers (ref, company_name, contact_name, email, phone, website, "
                "country, city, address, stage, source, owner, tags, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ref, form["company_name"].strip(), form.get("contact_name"),
                 form["email"].strip().lower(), form.get("phone"), form.get("website"),
                 form.get("country"), form.get("city"), form.get("address"),
                 form.get("stage") or "LEAD", form.get("source") or "OUTBOUND",
                 form.get("owner") or g.user["name"], form.get("tags"), form.get("notes")),
            )
            execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
                    (cid, "Customer created", g.user["email"]))
            flash("Customer added.", "ok")
            return redirect(url_for("admin.crm_detail", customer_id=cid))
    return render_template("admin/crm_new.html")


@bp.route("/crm/<int:customer_id>", methods=("GET", "POST"))
def crm_detail(customer_id):
    customer = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    if customer is None:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.crm"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "note":
            body = (request.form.get("body") or "").strip()
            if body:
                execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, ?, ?, ?)",
                        (customer_id, request.form.get("kind") or "NOTE", body, g.user["email"]))
                flash("Logged.", "ok")
        elif action == "stage":
            execute("UPDATE customers SET stage = ?, updated_at = ? WHERE id = ?",
                    (request.form.get("stage"), now_str(), customer_id))
            execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
                    (customer_id, f"Stage → {request.form.get('stage')}", g.user["email"]))
        elif action == "update":
            form = request.form
            execute(
                "UPDATE customers SET company_name = ?, contact_name = ?, email = ?, phone = ?, "
                "website = ?, country = ?, city = ?, address = ?, owner = ?, tags = ?, notes = ?, "
                "updated_at = ? WHERE id = ?",
                (form.get("company_name"), form.get("contact_name"), form.get("email"),
                 form.get("phone"), form.get("website"), form.get("country"), form.get("city"),
                 form.get("address"), form.get("owner"), form.get("tags"), form.get("notes"),
                 now_str(), customer_id))
            flash("Customer updated.", "ok")
        elif action == "portal":
            customer = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
            uid, pw = ensure_portal_user(customer)
            if pw:
                flash(f"Portal created for {customer['email']} — temporary password: {pw}", "ok")
                mail.send(customer["email"], f"Your {current_app.config['COMPANY_NAME']} portal",
                          template="portal_invite", customer=customer, password=pw,
                          company=current_app.config["COMPANY_NAME"],
                          site_url=current_app.config["SITE_URL"])
            else:
                flash("This customer already has a portal login.", "ok")
        elif action == "membership":
            new_status = request.form.get("membership_status")
            execute("UPDATE customers SET membership_status = ?, member_since = "
                    "CASE WHEN ? = 'MEMBER' AND member_since IS NULL THEN ? ELSE member_since END, "
                    "updated_at = ? WHERE id = ?",
                    (new_status, new_status, now_str(), now_str(), customer_id))
            execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                    "VALUES (?, 'SYSTEM', ?, ?)",
                    (customer_id, f"Membership -> {new_status}", g.user["email"]))
            flash("Membership updated.", "ok")
        elif action == "tags":
            tags = catalog_mod.format_tags(request.form.get("catalog_tags"))
            execute("UPDATE customers SET catalog_tags = ?, updated_at = ? WHERE id = ?",
                    (tags, now_str(), customer_id))
            execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                    "VALUES (?, 'SYSTEM', ?, ?)",
                    (customer_id, f"Catalog tags set to: {tags or 'none'}", g.user["email"]))
            flash("Tags updated — their portal reflects it immediately.", "ok")
        elif action == "freight_offer":
            on = 1 if request.form.get("freight_waived_default") else 0
            execute("UPDATE customers SET freight_waived_default = ?, updated_at = ? WHERE id = ?",
                    (on, now_str(), customer_id))
            execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                    "VALUES (?, 'SYSTEM', ?, ?)",
                    (customer_id, "Standing freight offer " + ("enabled" if on else "removed"),
                     g.user["email"]))
            flash("Standing freight offer " + ("enabled — new orders come through free."
                  if on else "removed."), "ok")
        elif action == "quota":
            membership.raise_limit(customer_id, to_int(request.form.get("quote_limit"), 10),
                                   request.form.get("membership_note"), g.user["email"])
            flash("Quote cycle limit updated.", "ok")
        elif action == "reset_password":
            from ..auth import generate_password
            from werkzeug.security import generate_password_hash
            user = query("SELECT * FROM users WHERE customer_id = ? ORDER BY id LIMIT 1",
                         (customer_id,), one=True)
            if user:
                pw = generate_password()
                execute("UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                        (generate_password_hash(pw), user["id"]))
                flash(f"New temporary password for {user['email']}: {pw}", "ok")
        return redirect(url_for("admin.crm_detail", customer_id=customer_id))

    activities = query(
        "SELECT * FROM crm_activities WHERE customer_id = ? ORDER BY created_at DESC, id DESC LIMIT 60",
        (customer_id,))
    quotes_rows = query("SELECT * FROM quotes WHERE customer_id = ? ORDER BY created_at DESC",
                        (customer_id,))
    orders_rows = query("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
                        (customer_id,))
    assigned = query(
        "SELECT i.*, a.custom_price_cents, a.custom_moq, a.note, a.assigned_at "
        "FROM catalog_assignments a JOIN catalog_items i ON i.id = a.item_id "
        "WHERE a.customer_id = ? ORDER BY a.assigned_at DESC", (customer_id,))
    unassigned = query(
        "SELECT * FROM catalog_items WHERE is_active = 1 AND id NOT IN "
        "(SELECT item_id FROM catalog_assignments WHERE customer_id = ?) ORDER BY name",
        (customer_id,))
    events = query(
        "SELECT * FROM calendar_events WHERE customer_id = ? ORDER BY starts_at DESC LIMIT 12",
        (customer_id,))
    portal_user = query("SELECT * FROM users WHERE customer_id = ? ORDER BY id LIMIT 1",
                        (customer_id,), one=True)
    applications_rows = query(
        "SELECT * FROM applications WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    return render_template(
        "admin/crm_detail.html", customer=customer, activities=activities, quotes=quotes_rows,
        orders=orders_rows, assigned=assigned, unassigned=unassigned, events=events,
        portal_user=portal_user, applications=applications_rows,
        quota=membership.quota_state(customer),
        visible_items=catalog_mod.items_for_customer(customer),
        all_tags=catalog_mod.all_tags())


# --------------------------------------------------------------------------
# calendar
# --------------------------------------------------------------------------
@bp.route("/calendar")
def calendar_view():
    today = utcnow().date()
    year = to_int(request.args.get("year"), today.year)
    month = to_int(request.args.get("month"), today.month)
    if not 1 <= month <= 12:
        year, month = today.year, today.month

    first = date(year, month, 1)
    last = date(year, month, pycal.monthrange(year, month)[1])
    grid_start = first - timedelta(days=(first.weekday() + 1) % 7)  # weeks start Sunday
    grid_end = last + timedelta(days=(6 - ((last.weekday() + 1) % 7)))

    events = query(
        "SELECT e.*, c.company_name FROM calendar_events e LEFT JOIN customers c ON c.id = e.customer_id "
        "WHERE date(e.starts_at) BETWEEN ? AND ? ORDER BY e.starts_at",
        (grid_start.isoformat(), grid_end.isoformat()))
    by_day = {}
    for e in events:
        dt = parse(e["starts_at"])
        if dt:
            by_day.setdefault(dt.date().isoformat(), []).append(e)

    weeks, cur = [], grid_start
    while cur <= grid_end:
        week = []
        for _ in range(7):
            week.append({"date": cur, "in_month": cur.month == month,
                         "today": cur == today, "events": by_day.get(cur.isoformat(), [])})
            cur += timedelta(days=1)
        weeks.append(week)

    upcoming = query(
        "SELECT e.*, c.company_name FROM calendar_events e LEFT JOIN customers c ON c.id = e.customer_id "
        "WHERE e.starts_at >= ? ORDER BY e.starts_at LIMIT 12", (now_str(),))
    prev_m = (first - timedelta(days=1))
    next_m = (last + timedelta(days=1))
    return render_template(
        "admin/calendar.html", weeks=weeks, year=year, month=month,
        month_name=pycal.month_name[month], upcoming=upcoming,
        prev={"year": prev_m.year, "month": prev_m.month},
        next={"year": next_m.year, "month": next_m.month},
        customers=query("SELECT id, company_name FROM customers ORDER BY company_name"),
        event_kinds=["CALL", "MEETING", "INTERVIEW", "FACTORY", "SHIPMENT",
                     "FOLLOWUP", "DEADLINE"])


@bp.route("/calendar/new", methods=("POST",))
def calendar_new():
    form = request.form
    starts = (form.get("starts_at") or "").replace("T", " ")
    if len(starts) == 16:
        starts += ":00"
    if not form.get("title") or not starts:
        flash("An event needs a title and a start time.", "error")
        return redirect(url_for("admin.calendar_view"))
    ends = (form.get("ends_at") or "").replace("T", " ")
    if ends and len(ends) == 16:
        ends += ":00"
    execute(
        "INSERT INTO calendar_events (title, customer_id, kind, starts_at, ends_at, location, notes, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (form["title"].strip(), to_int(form.get("customer_id")) or None,
         form.get("kind") or "MEETING", starts, ends or None, form.get("location"),
         form.get("notes"), g.user["email"]))
    flash("Event added to the calendar.", "ok")
    ref = parse(starts)
    return redirect(url_for("admin.calendar_view", year=ref.year, month=ref.month) if ref
                    else url_for("admin.calendar_view"))


@bp.route("/calendar/<int:event_id>/done", methods=("POST",))
def calendar_done(event_id):
    execute("UPDATE calendar_events SET done = 1 - done WHERE id = ?", (event_id,))
    return redirect(request.referrer or url_for("admin.calendar_view"))


@bp.route("/calendar/<int:event_id>/delete", methods=("POST",))
def calendar_delete(event_id):
    execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    flash("Event removed.", "ok")
    return redirect(request.referrer or url_for("admin.calendar_view"))


# --------------------------------------------------------------------------
# private catalog
# --------------------------------------------------------------------------
@bp.route("/catalog")
def catalog():
    items = query(
        "SELECT i.*, (SELECT COUNT(*) FROM catalog_assignments a WHERE a.item_id = i.id) AS assignees "
        "FROM catalog_items i ORDER BY i.is_active DESC, i.created_at DESC")
    reach = {i["id"]: len(catalog_mod.customers_for_item(i)) for i in items}
    return render_template("admin/catalog.html", items=items, reach=reach,
                           all_tags=catalog_mod.all_tags())


@bp.route("/catalog/new", methods=("GET", "POST"))
def catalog_new():
    if request.method == "POST":
        form = request.form
        sku = (form.get("sku") or "").strip().upper()
        if not sku or not form.get("name"):
            flash("SKU and name are required.", "error")
        elif query("SELECT id FROM catalog_items WHERE sku = ?", (sku,), one=True):
            flash("That SKU already exists.", "error")
        else:
            item_id = execute(
                "INSERT INTO catalog_items (sku, name, category, description, specs, materials, "
                "unit_price_cents, moq, lead_time_days, image_url, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sku, form["name"].strip(), form.get("category"), form.get("description"),
                 form.get("specs"), form.get("materials"), to_cents(form.get("unit_price")),
                 to_int(form.get("moq"), 1), to_int(form.get("lead_time_days"), 30),
                 form.get("image_url"), catalog_mod.format_tags(form.get("tags"))))
            flash("Catalog item created.", "ok")
            return redirect(url_for("admin.catalog_detail", item_id=item_id))
    return render_template("admin/catalog_form.html", item=None)


@bp.route("/catalog/<int:item_id>", methods=("GET", "POST"))
def catalog_detail(item_id):
    item = query("SELECT * FROM catalog_items WHERE id = ?", (item_id,), one=True)
    if item is None:
        flash("Item not found.", "error")
        return redirect(url_for("admin.catalog"))

    if request.method == "POST":
        action = request.form.get("action")
        form = request.form
        if action == "update":
            execute(
                "UPDATE catalog_items SET name = ?, category = ?, description = ?, specs = ?, "
                "materials = ?, unit_price_cents = ?, moq = ?, lead_time_days = ?, image_url = ?, "
                "tags = ?, is_active = ?, updated_at = ? WHERE id = ?",
                (form.get("name"), form.get("category"), form.get("description"), form.get("specs"),
                 form.get("materials"), to_cents(form.get("unit_price")), to_int(form.get("moq"), 1),
                 to_int(form.get("lead_time_days"), 30), form.get("image_url"),
                 catalog_mod.format_tags(form.get("tags")),
                 1 if form.get("is_active") else 0, now_str(), item_id))
            flash("Item updated.", "ok")
        elif action == "assign":
            cid = to_int(form.get("customer_id"))
            if cid:
                execute(
                    "INSERT INTO catalog_assignments (item_id, customer_id, custom_price_cents, "
                    "custom_moq, note, assigned_by) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(item_id, customer_id) DO UPDATE SET "
                    "custom_price_cents = excluded.custom_price_cents, custom_moq = excluded.custom_moq, "
                    "note = excluded.note",
                    (item_id, cid, to_cents(form.get("custom_price")) or None,
                     to_int(form.get("custom_moq")) or None, form.get("note"), g.user["email"]))
                execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
                        (cid, f"Catalog item {item['sku']} assigned to their portal", g.user["email"]))
                flash("Assigned — it's now visible in that client's portal.", "ok")
        elif action == "unassign":
            cid = to_int(form.get("customer_id"))
            execute("DELETE FROM catalog_assignments WHERE item_id = ? AND customer_id = ?",
                    (item_id, cid))
            flash("Removed from that client's portal.", "ok")
        return redirect(url_for("admin.catalog_detail", item_id=item_id))

    assignments = query(
        "SELECT a.*, c.company_name, c.ref FROM catalog_assignments a "
        "JOIN customers c ON c.id = a.customer_id WHERE a.item_id = ? ORDER BY a.assigned_at DESC",
        (item_id,))
    available = query(
        "SELECT * FROM customers WHERE id NOT IN "
        "(SELECT customer_id FROM catalog_assignments WHERE item_id = ?) ORDER BY company_name",
        (item_id,))
    return render_template("admin/catalog_detail.html", item=item, assignments=assignments,
                           available=available, reach=catalog_mod.customers_for_item(item),
                           all_tags=catalog_mod.all_tags())


# --------------------------------------------------------------------------
# order log + review gate
# --------------------------------------------------------------------------
@bp.route("/orders")
def orders():
    status = request.args.get("status", "")
    sql = ("SELECT o.*, c.company_name, c.ref AS customer_ref FROM orders o "
           "JOIN customers c ON c.id = o.customer_id ")
    args = []
    if status == "review":
        sql += "WHERE o.status = 'IN_REVIEW' "
    elif status == "open":
        sql += "WHERE o.status NOT IN ('DELIVERED','CANCELLED','REFUNDED') "
    elif status:
        sql += "WHERE o.status = ? "
        args.append(status)
    sql += "ORDER BY o.created_at DESC"
    rows = query(sql, args)
    totals = {
        "paid": sum(o["total_cents"] for o in rows if o["payment_status"] == "PAID"),
        "unpaid": sum(o["total_cents"] for o in rows if o["payment_status"] != "PAID"),
    }
    return render_template("admin/orders.html", orders=rows, status=status, totals=totals)


@bp.route("/orders/<int:order_id>", methods=("GET", "POST"))
def order_detail(order_id):
    order = orders_mod.get_order(order_id)
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("admin.orders"))
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "approve":
                orders_mod.approve_review(order_id, g.user["name"] or g.user["email"],
                                          request.form.get("notes"),
                                          start_production=request.form.get("start_production") == "1")
                flash("Review cleared — the order is released to production.", "ok")
            elif action == "hold":
                orders_mod.hold_order(order_id, g.user["name"] or g.user["email"],
                                      request.form.get("reason") or "Held during review")
                flash("Order placed on hold and the client has been notified.", "ok")
            elif action == "ship":
                orders_mod.ship_order(order_id, g.user["name"] or g.user["email"],
                                      request.form.get("carrier"), request.form.get("tracking"))
                flash("Marked as shipped.", "ok")
            elif action in ("waive", "unwaive"):
                orders_mod.set_freight_waived(
                    order_id, action == "waive", g.user["name"] or g.user["email"],
                    request.form.get("note"))
                flash("Freight and customs absorbed — the client sees it struck through."
                      if action == "waive" else "Freight and customs reinstated.", "ok")
            elif action == "tracking":
                carrier = (request.form.get("carrier") or "").strip() or None
                tracking = (request.form.get("tracking") or "").strip() or None
                execute("UPDATE orders SET carrier = ?, tracking_number = ?, updated_at = ? "
                        "WHERE id = ?", (carrier, tracking, now_str(), order_id))
                orders_mod.log_event(order_id, "TRACKING_UPDATED",
                                     f"{carrier or 'Carrier'} {tracking or '—'}".strip(),
                                     g.user["email"])
                if request.form.get("notify") and tracking:
                    order = orders_mod.get_order(order_id)
                    mail.send(customer["email"], f"Tracking for {order['ref']}",
                              template="order_tracking", order=order, customer=customer,
                              company=current_app.config["COMPANY_NAME"],
                              site_url=current_app.config["SITE_URL"], pretty_dt=pretty_dt)
                    flash("Tracking saved and the client has been emailed.", "ok")
                else:
                    flash("Tracking saved — it's live in their portal.", "ok")
            elif action == "deliver":
                execute("UPDATE orders SET status = 'DELIVERED', delivered_at = ?, updated_at = ? "
                        "WHERE id = ?", (now_str(), now_str(), order_id))
                orders_mod.log_event(order_id, "DELIVERED", None, g.user["email"])
            elif action == "mark_paid":
                orders_mod.confirm_funds(order_id, method=request.form.get("method") or "WIRE",
                                         payment_ref=request.form.get("payment_ref"),
                                         provider="manual", actor=g.user["email"])
                flash("Funds marked confirmed — review window opened and the orders inbox notified.", "ok")
            elif action == "cancel":
                execute("UPDATE orders SET status = 'CANCELLED', updated_at = ? WHERE id = ?",
                        (now_str(), order_id))
                orders_mod.log_event(order_id, "CANCELLED", request.form.get("reason"), g.user["email"])
                flash("Order cancelled.", "ok")
            elif action == "adjust":
                execute("UPDATE orders SET shipping_cents = ?, tax_cents = ?, notes = ?, updated_at = ? "
                        "WHERE id = ?",
                        (to_cents(request.form.get("shipping")), to_cents(request.form.get("tax")),
                         request.form.get("notes"), now_str(), order_id))
                orders_mod.recalc_totals(order_id)
                flash("Order totals updated.", "ok")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    est = orders_mod.freight_estimate(order)
    from ..freight import breakdown_lines
    return render_template(
        "admin/order_detail.html", order=order, customer=customer,
        items=orders_mod.get_items(order_id),
        events=query("SELECT * FROM order_events WHERE order_id = ? ORDER BY id DESC", (order_id,)),
        state=orders_mod.review_state(order),
        estimate=est, freight_lines=breakdown_lines(est) if est else [])


# --------------------------------------------------------------------------
# ops
# --------------------------------------------------------------------------
@bp.route("/emails")
def emails():
    return render_template(
        "admin/emails.html",
        emails=query("SELECT * FROM email_log ORDER BY created_at DESC, id DESC LIMIT 100"))


@bp.route("/settings", methods=("GET", "POST"))
def settings():
    if request.method == "POST" and request.form.get("action") == "add_admin":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or len(password) < 8:
            flash("An email and a password of at least 8 characters are required.", "error")
        elif query("SELECT id FROM users WHERE email = ?", (email,), one=True):
            flash("That email already has an account.", "error")
        else:
            create_user(email, password, name=request.form.get("name"), role="ADMIN")
            flash("Admin user created.", "ok")
        return redirect(url_for("admin.settings"))
    return render_template(
        "admin/settings.html",
        admins=query("SELECT * FROM users WHERE role = 'ADMIN' ORDER BY created_at"),
        webhooks=query("SELECT * FROM webhook_log ORDER BY id DESC LIMIT 25"))
