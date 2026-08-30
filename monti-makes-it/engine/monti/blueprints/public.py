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

from .. import assistant, catalogue, community, consults, disclaimers as disc
from .. import intake, mail, membership
from ..auth import ensure_portal_user
from ..db import execute, next_ref, query
from ..utils import money, now_str, pretty_dt, to_cents, to_int

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


@bp.route("/disclaimers")
@bp.route("/disclaimers/<slug>")
def disclaimers_page(slug=None):
    """CHG-024 — the disclaimers, and the version of each that is live.

    Every version carries the date it was published and the hash that identifies
    it, shown rather than hidden: a member who accepted something needs to be
    able to tell whether what they are reading now is what they agreed to.
    """
    live = disc.current()
    chosen = next((d for d in live if d["slug"] == slug), None) if slug else None
    return render_template("public/disclaimers.html", disclaimers=live, chosen=chosen)


@bp.route("/privacy")
def privacy():
    """CHG-025 — what is held and what is never sold.

    The same versioned machinery as the other disclaimers, on its own route
    because people look for it by that name.
    """
    version = disc.current("privacy")
    return render_template("public/disclaimers.html", disclaimers=disc.current(),
                           chosen=version, privacy_only=True)


@bp.route("/feedback", methods=("GET", "POST"))
def feedback():
    """CHG-033 — tell us what is wrong. It reaches a person and it is kept.

    Stored first, emailed second. A complaint whose only record was a failed SMTP
    connection is a complaint we never received.
    """
    if request.method == "POST":
        try:
            _row, emailed = community.leave_feedback(
                request.form.get("message"),
                name=request.form.get("name"),
                email=request.form.get("email"),
                kind=request.form.get("kind") or "GENERAL",
                page=request.form.get("page"),
                user_id=g.user["id"] if g.user else None,
                customer_id=g.customer["id"] if g.get("customer") else None)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("public/feedback.html", kinds=community.KINDS,
                                   form=request.form), 400
        flash("Thank you — that is with us." if emailed else
              "Thank you — that is saved. Our mail is having trouble, so we will "
              "see it in the portal rather than the inbox.", "ok")
        return redirect(url_for("public.feedback"))
    return render_template("public/feedback.html", kinds=community.KINDS, form={})


@bp.route("/reviews", methods=("GET", "POST"))
def testimonials():
    """CHG-034 — what other people say, and a way to add to it.

    Published reviews come from `community.published`, whose WHERE clause is the
    moderation. Nothing is seeded: a made-up review is a lie about a customer who
    does not exist, and it is the §1.5 breach people find easiest to excuse.
    """
    if request.method == "POST":
        try:
            community.submit_testimonial(
                request.form.get("author_name"), request.form.get("email"),
                request.form.get("body"),
                author_role=request.form.get("author_role"),
                company_name=request.form.get("company_name"),
                customer_id=g.customer["id"] if g.get("customer") else None)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("public/testimonials.html",
                                   reviews=community.published(),
                                   form=request.form), 400
        flash("Thank you. A person reads every review before it goes up — we will "
              "email you either way.", "ok")
        return redirect(url_for("public.testimonials"))
    return render_template("public/testimonials.html",
                           reviews=community.published(), form={})


@bp.route("/ask", methods=("POST",))
def ask():
    """CHG-029 — the question box in the corner.

    Answers only from text already published on this site, and returns the link
    to the page it came from. It has no language model behind it, on purpose:
    see the module docstring. A JSON endpoint so the widget does not reload the
    page underneath somebody.
    """
    question = (request.form.get("q") or "").strip()[:400]
    result = assistant.answer(question, faqs=FAQS)
    return {
        "found": result["found"],
        "reply": result["reply"],
        "links": [{"title": h["title"], "where": h["where"],
                   "url": url_for(h["endpoint"])} for h in result["hits"]],
    }


@bp.route("/faq")
def faq():
    """CHG-028 — questions people actually asked.

    No answer here states a price, a lead time or a capacity figure. Those change,
    and a stale FAQ answer is a quoted number nobody published (§11.1). Where an
    answer would need one, it points at the surface that holds the live figure.
    """
    return render_template("public/faq.html", faqs=FAQS)


# The questions, and where each answer's truth lives. Kept beside the route so a
# new answer has to name its source before it can be added.
FAQS = [
    ("Applying", [
        ("Do I have to be a company?",
         "No. Individuals apply on the same form. Company name, website and the "
         "questions about what you sell are optional — fill in what applies to you.",
         "public/apply.html"),
        ("What happens after I apply?",
         "A person reads it — every application, not a filter. If we want to talk, "
         "you pick a time from the slots we offer. If we decline, you get a reason "
         "and a way to reply.",
         "monti/blueprints/admin.py:applications"),
        ("Can I apply again if I am declined?",
         "You can reply to the decision on the same application rather than starting "
         "over. Reapplying is not blocked, but a reviewer will see that we have "
         "spoken before.",
         "CHG-026"),
    ]),
    ("Getting a price", [
        ("How do I get a quote?",
         "Describe what you want made — badly is fine. A sketch, a photograph, a "
         "voice note, a competitor's listing, or your current supplier's quote all "
         "work. We structure it into a specification.",
         "public/quote.html"),
        ("How long does a quote take?",
         "There is a clock on every request and it is shown to you on the request "
         "itself, counting down. We do not publish an average here because the "
         "figure on your request is the real one.",
         "portal/requests.html"),
        ("Why does a price need a person to sign it?",
         "Because a number nobody checked is a guess. A named manufacturing "
         "engineer signs the specification before it becomes a price, and that "
         "signature is a record, not a phone call.",
         "WI-I-03"),
    ]),
    ("Buying", [
        ("What am I actually paying for?",
         "Goods, freight and customs to your address, a convenience fee, and card "
         "or bank processing at cost. Every line is itemised at checkout before you "
         "pay — including the ones most quotes leave out.",
         "portal/checkout.html"),
        ("Can I change how it ships?",
         "Yes. Ocean, split and air are priced separately and you choose at the "
         "point of buying. The arrival method you pick is the one you are quoted.",
         "portal/products.html"),
        ("Do you keep my payment details?",
         "No. Card and bank details go to the payment provider and never reach our "
         "database. What we hold is described on the privacy page.",
         "/privacy"),
    ]),
    ("What we can make", [
        ("Is there anything you will not manufacture?",
         "Yes. What may lawfully be made and shipped depends on the product and on "
         "the laws where it is made, where it travels and where it lands. Requests "
         "in restricted categories are held for review by a person before pricing.",
         "/disclaimers/restricted"),
        ("Do you sell my information?",
         "No, and there is a page saying so that is checked against the system's "
         "own data map rather than against itself.",
         "/privacy"),
    ]),
]


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
    # One door (monti/intake.py). This form and "describe it badly" in the portal
    # are the same act, so both write the same records through the same function.
    # The only difference is how much of the specification arrives with it: this
    # form asks for all of it, the portal asks four rough questions. Neither
    # invents the fields the other collected.
    quote_row, item_row = intake.create_request(
        existing,
        title=form["title"].strip(),
        description=form["description"].strip(),
        source=(form.get("brought") or "").strip() or "A written description",
        weight=to_int(form.get("weight"), intake.DEFAULT_WEIGHT),
        author="website",
        category=form.get("category"),
        quantity=to_int(form.get("quantity"), 0),
        quantity_unit=form.get("quantity_unit") or "units",
        target_unit_price_cents=to_cents(form.get("target_unit_price")),
        materials=form.get("materials"), dimensions=form.get("dimensions"),
        color_finish=form.get("color_finish"), packaging=form.get("packaging"),
        certifications=form.get("certifications"),
        destination_country=form.get("destination_country"),
        destination_city=form.get("destination_city"),
        incoterm=form.get("incoterm") or "DDP", needed_by=form.get("needed_by"))
    quote_id, q_ref = quote_row["id"], quote_row["ref"]

    saved = _save_uploads(quote_id, request.files.getlist("files"))

    password = None
    if membership.is_member(existing):
        ensure_portal_user(existing, name=form["contact_name"].strip())

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
def _booking_context(form=None):
    """Everything the picker needs, and nothing it could use to invent a slot.

    The slots go out as UTC timestamps rather than as a pre-built calendar. Which
    DAY a slot falls on depends on the reader's timezone — 01:30 UTC is Tuesday
    night in London and Tuesday afternoon in Los Angeles — so grouping them into
    days here would put them on the wrong date for anyone far from the host.
    """
    open_slots = consults.slots()
    zones = list(consults.COMMON_ZONES)
    default_tz = consults.valid_zone((form or {}).get("consult_tz")) or "UTC"
    if default_tz not in zones:
        zones.insert(0, default_tz)
    return {
        # Passed as a list, rendered with |tojson. Building the JSON here and
        # printing it raw would need |safe, and |safe on anything that ever grows
        # a user-supplied field is a script injection waiting to happen. |tojson
        # escapes for a script context and cannot be got wrong later.
        "slot_data": [{"t": s.replace(" ", "T") + "Z", "m": m} for s, m in open_slots],
        "slot_days": bool(open_slots),
        "zones": zones,
        "default_tz": default_tz,
        "channels": consults.CHANNELS,
    }


@bp.route("/apply", methods=("GET", "POST"))
def apply():
    if request.method == "GET":
        return render_template("public/apply.html", form={}, categories=CATEGORIES,
                               volumes=VOLUME_BANDS, business_types=BUSINESS_TYPES,
                               **_booking_context())

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

    # CHG-021 — a posted slot is not a click. It can be edited, replayed, or sent
    # by something that never rendered the page, so it is checked against real
    # availability here rather than trusted because the picker produced it.
    slot = (form.get("consult_slot") or "").strip()
    if slot and not consults.is_open(slot):
        errors.append("That consultation time is no longer available. Please pick another.")
    if slot and form.get("consult_channel") == "phone" and not (form.get("consult_phone") or "").strip():
        errors.append("A phone consultation needs a number for us to call.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("public/apply.html", form=form, categories=CATEGORIES,
                               volumes=VOLUME_BANDS, business_types=BUSINESS_TYPES,
                               **_booking_context(form)), 400

    application, customer = membership.create_application(form)

    booking = None
    if slot:
        try:
            booking = consults.book(
                application, slot,
                guest_tz=form.get("consult_tz"),
                channel=form.get("consult_channel") or "video",
                phone=form.get("consult_phone"),
                note=form.get("consult_note"))
        except (consults.SlotGone, ValueError) as exc:
            # The application is already saved and that is deliberate: losing
            # everything they typed because a slot went in the last two seconds
            # would be the worse failure. They are told, and can book from the
            # confirmation page.
            flash(f"Your application is in — but we could not hold that time: {exc}. "
                  "Pick another below.", "error")

    return render_template("public/apply_received.html", application=application,
                           customer=customer, booking=booking,
                           booking_tz=consults.valid_zone(form.get("consult_tz")) or "UTC")
