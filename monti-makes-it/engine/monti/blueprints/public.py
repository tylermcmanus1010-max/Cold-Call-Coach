"""The public site.

Two doors, and nothing else competing for attention:

    Request a quote      — open to anyone. Tell us what you want made.
    Apply for membership — screened, interviewed, and decided by a person.
                           Membership is what unlocks buying.
"""
import uuid
from pathlib import Path

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for,
)
from werkzeug.utils import secure_filename

from .. import catalogue, mail, membership
from ..auth import ensure_portal_user
from ..db import execute, next_ref, query
from ..utils import money, now_str, plus_hours, pretty_dt, to_cents, to_int

bp = Blueprint("public", __name__)

CATEGORIES = [
    "Apparel & textiles", "Bags & leather goods", "Packaging & print",
    "Metal & machined parts", "Molded plastics", "Electronics & assemblies",
    "Furniture & fixtures", "Silicone & rubber", "Ceramics & glass", "Something else",
]

VOLUME_BANDS = [
    "Under $50k a year", "$50k – $250k", "$250k – $1M", "$1M – $5M", "Over $5M",
    "Just getting started",
]

BUSINESS_TYPES = [
    "Brand selling my own products", "Retailer", "Distributor or wholesaler",
    "Agency buying for clients", "Startup launching a first product", "Something else",
]


@bp.route("/")
def home():
    return render_template("public/home.html")


@bp.route("/how-it-works")
def how_it_works():
    return render_template("public/how_it_works.html")


@bp.route("/membership")
def membership_page():
    return render_template("public/membership.html")


@bp.route("/contact")
def contact():
    return render_template("public/contact.html")


# --------------------------------------------------------------------------
# door three — browse the catalogue (§8.2)
#
# Open to everyone, signed in or not. What is gated is buying, not looking, so
# these two routes take no customer parameter and never join a registration:
# there is nothing customer-shaped in scope for a negotiated price to leak from.
# The call to action is the one place the viewer's state matters, and it is
# computed by the same function the server-side gate uses.
# --------------------------------------------------------------------------
@bp.route("/catalogue")
def catalogue_index():
    items = catalogue.public_items()
    return render_template("public/catalogue.html", items=items,
                           range_text=catalogue.range_text)


@bp.route("/catalogue/<sku>")
def catalogue_item(sku):
    item = catalogue.public_item_by_sku(sku)
    if item is None:
        abort(404)
    customer = g.get("customer")
    return render_template("public/catalogue_item.html", item=item,
                           range_text=catalogue.range_text,
                           cta=catalogue.cta_state(customer, item["id"]),
                           customer=customer)


# --------------------------------------------------------------------------
# door one — request a quote
# --------------------------------------------------------------------------
@bp.route("/quote", methods=("GET", "POST"))
def quote():
    customer = g.get("customer")
    quota = membership.quota_state(customer) if customer else None

    if request.method == "GET":
        return render_template("public/quote.html", categories=CATEGORIES, form={},
                               quota=quota, customer=customer)

    form = request.form
    errors = []
    for field, label in {"contact_name": "Your name", "email": "Email",
                         "title": "What you want made",
                         "description": "The description"}.items():
        if not (form.get(field) or "").strip():
            errors.append(f"{label} is required.")
    if form.get("email") and "@" not in form["email"]:
        errors.append("That email address doesn't look right.")

    email = (form.get("email") or "").strip().lower()
    existing = query("SELECT * FROM customers WHERE lower(email) = ?", (email,), one=True)
    if existing:
        blocked = membership.check_quota(existing)
        if blocked:
            errors.append(blocked)

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("public/quote.html", categories=CATEGORIES, form=form,
                               quota=quota, customer=customer), 400

    if existing is None:
        cust_ref = next_ref("MMI-C", "customers", start=1001)
        customer_id = execute(
            "INSERT INTO customers (ref, company_name, contact_name, email, phone, "
            "country, stage, source, owner, membership_status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'QUOTING', 'WEBSITE', 'Unassigned', 'PROSPECT')",
            (cust_ref, (form.get("company_name") or form["contact_name"]).strip(),
             form["contact_name"].strip(), email, form.get("phone"), form.get("country")))
        existing = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    else:
        execute(
            "UPDATE customers SET stage = CASE WHEN stage IN ('LEAD','DORMANT','LOST') "
            "THEN 'QUOTING' ELSE stage END, updated_at = ? WHERE id = ?",
            (now_str(), existing["id"]))

    sla = current_app.config["QUOTE_SLA_HOURS"]
    q_ref = next_ref("MMI-Q", "quotes", start=1001)
    quote_id = execute(
        "INSERT INTO quotes (ref, customer_id, title, description, category, quantity, "
        "quantity_unit, target_unit_price_cents, materials, dimensions, color_finish, packaging, "
        "certifications, destination_country, destination_city, incoterm, needed_by, priority, due_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (q_ref, existing["id"], form["title"].strip(), form["description"].strip(),
         form.get("category"), to_int(form.get("quantity"), 0),
         form.get("quantity_unit") or "units", to_cents(form.get("target_unit_price")),
         form.get("materials"), form.get("dimensions"), form.get("color_finish"),
         form.get("packaging"), form.get("certifications"), form.get("destination_country"),
         form.get("destination_city"), form.get("incoterm") or "DDP", form.get("needed_by"),
         "NORMAL", plus_hours(sla)))

    saved = _save_uploads(quote_id, request.files.getlist("files"))

    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, 'website')",
            (existing["id"], f"Requested a quote — {q_ref}: {form['title'].strip()}"))
    execute(
        "INSERT INTO calendar_events (title, customer_id, kind, starts_at, notes, created_by) "
        "VALUES (?, ?, 'DEADLINE', ?, ?, 'system')",
        (f"Quote due · {q_ref}", existing["id"], plus_hours(sla),
         f"{sla}h estimate deadline for {existing['company_name']}."))

    password = None
    if membership.is_member(existing):
        ensure_portal_user(existing, name=form["contact_name"].strip())

    quote_row = query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True)
    cfg = current_app.config
    mail.send(existing["email"], f"We've got it — {q_ref}", template="quote_received",
              quote=quote_row, customer=existing, company=cfg["COMPANY_NAME"], sla=sla,
              pretty_dt=pretty_dt, site_url=cfg["SITE_URL"], password=password,
              login_email=existing["email"], files=saved,
              is_member=membership.is_member(existing))
    mail.send(cfg["QUOTES_EMAIL"],
              f"[QUOTE {q_ref}] {existing['company_name']} — {form['title'].strip()[:60]}",
              template="quote_internal", quote=quote_row, customer=existing,
              company=cfg["COMPANY_NAME"], sla=sla, pretty_dt=pretty_dt, money=money,
              site_url=cfg["SITE_URL"], files=saved)

    return render_template("public/quote_received.html", quote=quote_row, customer=existing,
                           sla=sla, file_count=len(saved),
                           is_member=membership.is_member(existing),
                           quota=membership.quota_state(existing))


def _save_uploads(quote_id, files):
    saved = []
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    allowed = current_app.config["ALLOWED_UPLOAD_EXT"]
    for f in files:
        if not f or not f.filename:
            continue
        name = secure_filename(f.filename)
        ext = Path(name).suffix.lower()
        if ext not in allowed:
            current_app.logger.warning("Rejected upload with extension %s", ext)
            continue
        stored = f"{uuid.uuid4().hex}{ext}"
        dest = upload_dir / stored
        f.save(dest)
        execute(
            "INSERT INTO quote_files (quote_id, filename, stored_name, content_type, size_bytes) "
            "VALUES (?, ?, ?, ?, ?)", (quote_id, name, stored, f.mimetype, dest.stat().st_size))
        saved.append({"filename": name, "size": dest.stat().st_size})
    return saved


# --------------------------------------------------------------------------
# door two — apply for membership
# --------------------------------------------------------------------------
@bp.route("/apply", methods=("GET", "POST"))
def apply():
    if request.method == "GET":
        return render_template("public/apply.html", form={}, categories=CATEGORIES,
                               volumes=VOLUME_BANDS, business_types=BUSINESS_TYPES)

    form = request.form
    errors = []
    for field, label in {"company_name": "Company name", "contact_name": "Your name",
                         "email": "Email", "what_they_sell": "What you sell",
                         "why": "Why you want to work with us"}.items():
        if not (form.get(field) or "").strip():
            errors.append(f"{label} is required.")
    if form.get("email") and "@" not in form["email"]:
        errors.append("That email address doesn't look right.")

    email = (form.get("email") or "").strip().lower()
    open_app = query(
        "SELECT * FROM applications WHERE lower(email) = ? AND status IN "
        "('SUBMITTED','SCREENING','INTERVIEW_SCHEDULED') ORDER BY id DESC LIMIT 1",
        (email,), one=True)
    if open_app:
        errors.append(
            f"You already have an application with us ({open_app['ref']}), and it's being reviewed. "
            "We'll be in touch — no need to send another.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("public/apply.html", form=form, categories=CATEGORIES,
                               volumes=VOLUME_BANDS, business_types=BUSINESS_TYPES), 400

    application, customer = membership.create_application(form)
    return render_template("public/apply_received.html", application=application, customer=customer)
