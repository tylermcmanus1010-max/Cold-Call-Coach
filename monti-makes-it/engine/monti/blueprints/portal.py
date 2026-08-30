"""Member portal — sealed per customer.

Every query in this module is scoped by `g.user['customer_id']`, and anything
fetched by id is passed through `own_or_404`. There is no route here that can
return another customer's row.

Browsing and quoting are open to any account with a login. Anything that spends
money is wrapped in `member_only` — acceptance is what unlocks buying.
"""
import csv
import functools
import io
from pathlib import Path

from flask import (
    Blueprint, Response, abort, current_app, flash, g, redirect,
    render_template, request, send_from_directory, url_for,
)

from .. import catalog as catalog_mod
from .. import catalogue
from .. import decisionroom as dr
from .. import disclaimers as disc
from .. import genome as genome_mod
from .. import intake as intake_mod
from .. import ledger
from .. import membership
from .. import orders as orders_mod
from .. import payments
from .. import tooling
from ..auth import client_required, own_or_404
from ..db import execute, query
from ..utils import money, now_str, to_cents, to_int

bp = Blueprint("portal", __name__, url_prefix="/portal")


def _cid():
    """The customer this request is scoped to — the member's own, or the one an
    admin has opened from the admin portal."""
    return g.customer["id"]


def _cart_rows():
    return query(
        """SELECT ci.*, i.name, i.sku, i.unit_price_cents AS list_price, i.moq, i.lead_time_days,
                  i.image_url, r.unit_price_cents AS unit_price_cents, r.moq AS moq
           FROM cart_items ci
           JOIN catalog_items i ON i.id = ci.item_id
           LEFT JOIN catalogue_registrations r
                  ON r.item_id = i.id AND r.customer_id = ci.customer_id AND r.active = 1
           WHERE ci.customer_id = ? ORDER BY ci.id""",
        (_cid(),),
    )


def _unregistered_lines(order_id):
    """Names of any catalogue lines on this order the member may no longer buy.

    Lines with no catalogue item behind them — an accepted estimate off a quote —
    are not catalogue purchases and are not gated by registration.
    """
    blocked = []
    for line in orders_mod.get_items(order_id):
        if line["catalog_item_id"] and not catalogue.can_order(g.customer, line["catalog_item_id"]):
            blocked.append(line["name"])
    return blocked


def _freight_lines(order):
    est = orders_mod.freight_estimate(order)
    if not est:
        return []
    from ..freight import breakdown_lines
    return breakdown_lines(est)


def _cart_summary():
    rows = _cart_rows()
    lines = []
    subtotal = 0
    for r in rows:
        unit = r["unit_price_cents"] if r["unit_price_cents"] is not None else r["list_price"]
        qty = max(1, r["quantity"])
        line_total = unit * qty
        subtotal += line_total
        lines.append({
            "cart_id": r["id"], "item_id": r["item_id"], "name": r["name"], "sku": r["sku"],
            "unit_price_cents": unit, "quantity": qty, "line_total_cents": line_total,
            "moq": r["moq"] or r["moq"], "lead_time_days": r["lead_time_days"],
        })
    return lines, subtotal


@bp.app_context_processor
def inject_portal_context():
    if g.get("user") and g.get("customer"):
        row = query("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ?", (_cid(),), one=True)
        return {
            "cart_count": row["c"],
            "quota": membership.quota_state(g.customer),
            "is_member": membership.is_member(g.customer),
        }
    return {}


def member_only(view):
    """Buying is what membership unlocks. Quoting and browsing are not gated."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if not membership.is_member(g.get("customer")):
            flash("Ordering is open to accepted members. Your application is the next step.", "error")
            return redirect(url_for("public.apply"))
        return view(**kwargs)
    return wrapped


# --------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------
@bp.route("/")
@client_required
def dashboard():
    cid = _cid()
    quotes = query(
        "SELECT * FROM quotes WHERE customer_id = ? ORDER BY created_at DESC LIMIT 6", (cid,)
    )
    active_orders = query(
        "SELECT * FROM orders WHERE customer_id = ? AND status NOT IN "
        "('DELIVERED','CANCELLED','REFUNDED') ORDER BY created_at DESC LIMIT 5", (cid,)
    )
    stats = {
        "open_quotes": query(
            "SELECT COUNT(*) AS c FROM quotes WHERE customer_id = ? AND status IN "
            "('NEW','IN_REVIEW','ESTIMATE_SENT')", (cid,), one=True)["c"],
        "awaiting_you": query(
            "SELECT COUNT(*) AS c FROM quotes WHERE customer_id = ? AND status = 'ESTIMATE_SENT'",
            (cid,), one=True)["c"],
        "open_orders": query(
            "SELECT COUNT(*) AS c FROM orders WHERE customer_id = ? AND status NOT IN "
            "('DELIVERED','CANCELLED','REFUNDED')", (cid,), one=True)["c"],
        "catalog_items": query(
            "SELECT COUNT(*) AS c FROM catalogue_registrations a "
            "JOIN catalog_items i ON i.id = a.item_id AND a.active = 1 "
            "WHERE a.customer_id = ? AND i.is_active = 1", (cid,), one=True)["c"],
    }
    estimates = {
        r["quote_id"]: r for r in query(
            "SELECT e.* FROM estimates e JOIN quotes q ON q.id = e.quote_id "
            "WHERE q.customer_id = ? ORDER BY e.created_at DESC", (cid,))
    }
    return render_template("portal/dashboard.html", quotes=quotes, orders=active_orders,
                           stats=stats, estimates=estimates)


# --------------------------------------------------------------------------
# quotes
# --------------------------------------------------------------------------
@bp.route("/quotes")
@client_required
def quotes():
    """Kept as a redirect. Quotes and "describe it badly" are one surface now.

    A member had two places to look at the same request — a Quotes tab with the
    clock and the estimate, and an intake form that created something else
    entirely. Both are `portal.requests_page`; this route survives only so that
    links in old emails and bookmarks still land somewhere real.
    """
    return redirect(url_for("portal.requests_page",
                            status=request.args.get("status", "") or None))


@bp.route("/quotes/<int:quote_id>")
@client_required
def quote_detail(quote_id):
    quote = own_or_404(query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True))
    estimate = query(
        "SELECT * FROM estimates WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
        (quote_id,), one=True)
    files = query("SELECT * FROM quote_files WHERE quote_id = ? ORDER BY id", (quote_id,))
    order = query("SELECT * FROM orders WHERE source_quote_id = ? ORDER BY id DESC LIMIT 1",
                  (quote_id,), one=True)
    return render_template("portal/quote_detail.html", quote=quote, estimate=estimate,
                           files=files, order=order)


@bp.route("/quotes/<int:quote_id>/accept", methods=("POST",))
@client_required
@member_only
def accept_quote(quote_id):
    quote = own_or_404(query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True))
    estimate = query("SELECT * FROM estimates WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
                     (quote_id,), one=True)
    if quote["status"] != "ESTIMATE_SENT" or estimate is None:
        flash("That quote isn't ready to accept.", "error")
        return redirect(url_for("portal.quote_detail", quote_id=quote_id))

    existing = query("SELECT * FROM orders WHERE source_quote_id = ? AND status NOT IN "
                     "('CANCELLED','REFUNDED') LIMIT 1", (quote_id,), one=True)
    if existing:
        return redirect(url_for("portal.order_detail", order_id=existing["id"]))

    execute("UPDATE quotes SET status = 'ACCEPTED', decided_at = ?, updated_at = ? WHERE id = ?",
            (now_str(), now_str(), quote_id))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
            (quote["customer_id"], f"Accepted estimate on {quote['ref']}", g.user["email"]))

    lines = [{
        "name": quote["title"],
        "sku": quote["ref"],
        "unit_price_cents": estimate["unit_price_cents"],
        "quantity": estimate["quantity"] or quote["quantity"] or 1,
        "quote_id": quote_id,
    }]
    for label, cents in (("Tooling (one-time)", estimate["tooling_cents"]),
                         ("Sampling", estimate["sample_cents"])):
        if cents:
            lines.append({"name": label, "sku": quote["ref"], "unit_price_cents": cents, "quantity": 1,
                          "quote_id": quote_id})

    order = orders_mod.create_order(
        customer_id=quote["customer_id"], lines=lines,
        source_quote_id=quote_id, actor=g.user["email"],
        notes=f"Converted from {quote['ref']}",
        category=quote["category"], destination=quote["destination_country"],
        ship_mode=(estimate["ship_method"] or "SEA"),
    )
    flash(f"Estimate accepted — order {order['ref']} created.", "ok")
    return redirect(url_for("portal.order_detail", order_id=order["id"]))


@bp.route("/quotes/<int:quote_id>/decline", methods=("POST",))
@client_required
def decline_quote(quote_id):
    quote = own_or_404(query("SELECT * FROM quotes WHERE id = ?", (quote_id,), one=True))
    reason = (request.form.get("reason") or "").strip()
    execute("UPDATE quotes SET status = 'DECLINED', decided_at = ?, updated_at = ? WHERE id = ?",
            (now_str(), now_str(), quote_id))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, 'SYSTEM', ?, ?)",
            (quote["customer_id"], f"Declined {quote['ref']}" + (f" — {reason}" if reason else ""),
             g.user["email"]))
    flash("Estimate declined. Nothing further will happen on it.", "ok")
    return redirect(url_for("portal.quote_detail", quote_id=quote_id))


@bp.route("/files/<int:file_id>")
@client_required
def download_file(file_id):
    row = query(
        "SELECT f.*, q.customer_id FROM quote_files f JOIN quotes q ON q.id = f.quote_id "
        "WHERE f.id = ?", (file_id,), one=True)
    own_or_404(row)
    return send_from_directory(current_app.config["UPLOAD_DIR"], row["stored_name"],
                               as_attachment=True, download_name=row["filename"])


# --------------------------------------------------------------------------
# private catalog
# --------------------------------------------------------------------------
@bp.route("/catalog")
@client_required
def catalog():
    items = catalog_mod.items_for_customer(g.customer)
    return render_template("portal/catalog.html", items=items,
                           tags=catalog_mod.parse_tags(g.customer["catalog_tags"]))


@bp.route("/catalog/<int:item_id>")
@client_required
def catalog_item(item_id):
    match = [i for i in catalog_mod.items_for_customer(g.customer) if i["id"] == item_id]
    if not match:
        abort(404)   # not reachable by this account = does not exist, as far as they know
    item = match[0]

    # The genome's internal partition never leaves the admin side (GEN-07), so
    # it is excluded in the query rather than filtered in the template — a
    # template filter is one `{% for %}` away from being forgotten.
    genome = query(
        "SELECT section, body, is_unknown FROM item_genome "
        "WHERE item_id = ? AND is_internal = 0 ORDER BY id", (item_id,))

    lines = []
    if catalogue.can_order(g.customer, item_id):
        quantity = max(item["moq"] or 1, 1)
        lines = tooling.lines_for(item_id, _cid(), quantity,
                                  item["price_cents"] or 0, strategy="lowest_cost")

    return render_template("portal/catalog_item.html", item=item,
                           images=catalogue.item_images(item_id),
                           genome=genome, tooling_lines=lines)


@bp.route("/cart/add/<int:item_id>", methods=("POST",))
@client_required
def cart_add(item_id):
    # Gate 1 of 3 (§8.4). Seeing an item and being able to order it are
    # different questions, and this is the second one. The template hides the
    # Order control for an unregistered item, but that is a courtesy — removing
    # the client-side check has to leave this refusal standing.
    if not catalogue.can_order(g.customer, item_id):
        abort(404)
    qty = max(1, to_int(request.form.get("quantity"), 1))
    existing = query("SELECT * FROM cart_items WHERE customer_id = ? AND item_id = ?",
                     (_cid(), item_id), one=True)
    if existing:
        execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (qty, existing["id"]))
    else:
        execute("INSERT INTO cart_items (customer_id, item_id, quantity) VALUES (?, ?, ?)",
                (_cid(), item_id, qty))
    flash("Added to your order.", "ok")
    return redirect(request.form.get("next") or url_for("portal.cart"))


@bp.route("/cart")
@client_required
def cart():
    lines, subtotal = _cart_summary()
    return render_template("portal/cart.html", lines=lines, subtotal=subtotal)


@bp.route("/cart/remove/<int:cart_id>", methods=("POST",))
@client_required
def cart_remove(cart_id):
    row = own_or_404(query("SELECT * FROM cart_items WHERE id = ?", (cart_id,), one=True))
    execute("DELETE FROM cart_items WHERE id = ?", (row["id"],))
    return redirect(url_for("portal.cart"))


@bp.route("/cart/checkout", methods=("POST",))
@client_required
@member_only
def cart_checkout():
    lines, subtotal = _cart_summary()
    if not lines:
        flash("Your order is empty.", "error")
        return redirect(url_for("portal.cart"))
    # Gate 2 of 3 (§8.4). Re-asked at order creation rather than trusted from
    # the add-to-cart call: a registration can be deactivated between the two,
    # and a cart row that predates the deactivation must not become an order.
    for line in lines:
        if line["item_id"] and not catalogue.can_order(g.customer, line["item_id"]):
            flash(f"{line['name']} is no longer registered to your account. "
                  "Request it and we'll pick it up from there.", "error")
            return redirect(url_for("portal.cart"))
        if line["quantity"] < (line["moq"] or 1):
            flash(f"{line['name']} has a minimum order of {line['moq']:,}.", "error")
            return redirect(url_for("portal.cart"))
    first_item = query("SELECT category FROM catalog_items WHERE id = ?",
                       (lines[0]["item_id"],), one=True) if lines[0].get("item_id") else None
    order = orders_mod.create_order(
        customer_id=_cid(),
        lines=[{"name": l["name"], "sku": l["sku"], "unit_price_cents": l["unit_price_cents"],
                "quantity": l["quantity"], "catalog_item_id": l["item_id"]} for l in lines],
        ship_to=(request.form.get("ship_to") or "").strip() or None,
        notes=(request.form.get("notes") or "").strip() or None,
        actor=g.user["email"],
        category=first_item["category"] if first_item else None,
        destination=g.customer["country"],
    )
    execute("DELETE FROM cart_items WHERE customer_id = ?", (_cid(),))
    return redirect(url_for("portal.checkout", order_id=order["id"]))


# --------------------------------------------------------------------------
# orders + checkout
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# requests — "describe it badly", which is also the quotes list
#
# One surface, because it is one act. A member used to have a Quotes tab (a
# reference, a 24-hour clock, an estimate to accept) and, separately, an intake
# form that created a product with none of those things. Watching a request
# meant watching two lists that did not know about each other, and the two
# counters over the same allowance each saw half the traffic.
#
# So the form and the list live on one page and write one record through
# `monti.intake.create_request`. Two rules survive the merge intact:
#
#   No spec reaches a price without a person (WI-I-03). Submitting creates a
#   product at stage 1, not a price. It advances when a named engineer has
#   signed the specification, which is a recorded event and not a timer.
#
#   A request that costs nothing says so before it is sent (E4.04). The capacity
#   a submission will consume is shown on the form, with the rule that a
#   declined or incomplete request is never charged.
# --------------------------------------------------------------------------
QUOTE_FILTERS = [
    ("NEW", "Submitted"), ("IN_REVIEW", "Being priced"),
    ("ESTIMATE_SENT", "Estimate ready"), ("ACCEPTED", "Accepted"),
    ("DECLINED", "Declined"),
]


@bp.route("/requests", methods=("GET", "POST"))
@client_required
def requests_page():
    if request.method == "POST":
        return _submit_request()

    status = request.args.get("status", "")
    sql = "SELECT * FROM quotes WHERE customer_id = ?"
    args = [_cid()]
    if status:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY created_at DESC"
    rows = query(sql, args)
    estimates = {r["quote_id"]: r for r in query(
        "SELECT e.* FROM estimates e JOIN quotes q ON q.id = e.quote_id WHERE q.customer_id = ?",
        (_cid(),))}
    # The product each request became, so a row can carry a link to the thing
    # rather than to a second record describing the same thing. Keyed by
    # quote id; a request that predates the merge simply has no entry.
    products = {r["quote_id"]: r for r in query(
        "SELECT * FROM decision_items WHERE customer_id = ? AND quote_id IS NOT NULL",
        (_cid(),))}

    return render_template(
        "portal/requests.html", quotes=rows, estimates=estimates, status=status,
        products=products, filters=QUOTE_FILTERS,
        formats=intake_mod.FORMATS, weights=intake_mod.WEIGHTS,
        capacity=genome_mod.capacity(g.customer), boxes=genome_mod.boxes(_cid()))


def _submit_request():
    """One submission. One quote, one product, one capacity debit."""
    summary = (request.form.get("summary") or "").strip()
    if not summary:
        flash("Tell us what you want made — a sentence is enough.", "error")
        return redirect(url_for("portal.requests_page"))

    # The same allowance gate the public form applies. It reads `quotes`, and
    # every request now writes one, so the counter finally sees all of them.
    blocked = membership.check_quota(g.customer)
    if blocked:
        flash(blocked, "error")
        return redirect(url_for("portal.requests_page"))

    quantity = (request.form.get("quantity") or "").strip()
    material = (request.form.get("material") or "").strip()
    needed_by = (request.form.get("needed_by") or "").strip()
    detail = " · ".join(filter(None, [quantity, material, needed_by]))

    quote_row, item_row = intake_mod.create_request(
        g.customer,
        title=summary,
        # The four rough answers are the description. They are stored as the
        # member wrote them — "a few hundred thousand a year" is not turned into
        # a number here, because nobody has agreed one yet.
        description=detail or summary,
        source=((request.form.get("brought") or "").strip() or "A written description")
        + (f" — {detail}" if detail else ""),
        weight=to_int(request.form.get("weight"), intake_mod.DEFAULT_WEIGHT),
        author="portal",
        materials=material or None,
        needed_by=needed_by or None,
        destination_country=g.customer["country"])

    flash(f"{item_row['ref']} is in your products, and {quote_row['ref']} is on the "
          f"pricing desk's clock. We come back within 24 hours.", "ok")
    return redirect(url_for("portal.products", ref=item_row["ref"]))


@bp.route("/intake", methods=("GET", "POST"))
@client_required
def intake():
    """The old intake URL. Same page, one address."""
    if request.method == "POST":
        return _submit_request()
    return redirect(url_for("portal.requests_page"))


@bp.route("/intake/box", methods=("POST",))
@client_required
def request_box():
    """Make This Box. Stage 0 until something is actually recorded against it."""
    count = query("SELECT COUNT(*) AS c FROM sample_boxes", one=True)["c"]
    ref = f"MMI-BOX-{4001 + count}"
    box_id = execute("INSERT INTO sample_boxes (ref, customer_id, stage) VALUES (?, ?, 0)",
                     (ref, _cid()))
    execute("INSERT INTO sample_events (box_id, stage, detail, recorded_by) "
            "VALUES (?, 0, 'Requested from the portal', 'portal')", (box_id,))
    flash(f"Box {ref} requested. It ships prepaid — put the thing inside and scan the "
          f"code on the lid.", "ok")
    return redirect(url_for("portal.requests_page"))


# --------------------------------------------------------------------------
# My products — the Decision Room, under the name a member would use for it
# (Appendix E.1)
#
# The tab is "My products" because that is what it holds: everything the member
# has asked us to make, in one list, from the request that arrived this morning
# to the part that has been running for a year. "Decision Room" survives as the
# name of what a *priced* product opens into — the three routes, the slider and
# the levers — which is a thing you enter, not a place your products live.
#
# Two rails down the left: what is waiting on us, and what has been priced and
# released. An item only reaches the second rail when an admin publishes, and
# the read below filters on `published_at` — so "no prices before publish" is a
# WHERE clause, not a convention.
# --------------------------------------------------------------------------
def _items_for_member():
    rows = query(
        "SELECT * FROM decision_items WHERE customer_id = ? ORDER BY received_at DESC",
        (_cid(),))
    return ([r for r in rows if r["status"] == "PENDING"],
            [r for r in rows if r["status"] == "APPROVED" and r["published_at"]])


@bp.route("/room")
@bp.route("/room/<ref>")
@client_required
def room(ref=None):
    """The tab was called the Decision Room. Old links keep working."""
    return redirect(url_for("portal.products", ref=ref) if ref
                    else url_for("portal.products"), code=301)


@bp.route("/contact")
@client_required
def contact():
    """CHG-031 — how to reach a person, from inside the portal.

    The account reference is filled in for them. Asking a member to go and find
    their own reference before they can ask a question is asking them to do our
    filing.
    """
    return render_template("portal/contact.html",
                           accepted=disc.acceptances_for(_cid()))


@bp.route("/products")
@bp.route("/products/<ref>")
@client_required
def products(ref=None):
    pending, approved = _items_for_member()
    chosen = None
    for row in pending + approved:
        if ref is None or row["ref"] == ref:
            chosen = row
            break

    view = None
    if chosen is not None and chosen["status"] == "APPROVED" and chosen["published_at"]:
        view = _room_view(chosen)

    # The request this product came from, so the clock and the estimate live on
    # the product rather than on a second page about the same thing. Products
    # migrated from before the merge have no quote, and the panel is omitted
    # rather than filled with a placeholder clock.
    quote = estimate = None
    if chosen is not None and chosen["quote_id"]:
        quote = query("SELECT * FROM quotes WHERE id = ? AND customer_id = ?",
                      (chosen["quote_id"], _cid()), one=True)
        if quote:
            estimate = query("SELECT * FROM estimates WHERE quote_id = ?",
                             (quote["id"],), one=True)

    return render_template("portal/products.html", pending=pending, approved=approved,
                           item=chosen, view=view, stages=DR_STAGES,
                           quote=quote, estimate=estimate)


DR_STAGES = ["Received", "Specification in review", "Priced — awaiting release"]


def _room_view(item):
    """Everything the priced view renders, computed once from the entered inputs."""
    costs = dr.cost_inputs(item["id"])
    lane_rows = dr.lanes()
    bounds = dr.quantity_bounds(item)
    if not costs or not lane_rows or not bounds:
        # Published but unpriceable: say so rather than rendering zeros.
        return {"incomplete": True, "bounds": bounds, "has_costs": bool(costs),
                "has_lanes": bool(lane_rows)}

    qty = to_int(request.args.get("qty"), 0) or bounds["min"]
    qty = max(bounds["min"], min(bounds["max"], qty))
    mode = request.args.get("mode") or "ocean"
    if mode not in lane_rows:
        mode = next(iter(lane_rows))
    # None means "as each route prices it". §11.3.3 gives the three strategies
    # different tooling defaults — lowest-cost amortizes, the other two charge
    # upfront — and forcing one treatment on all three by default erases exactly
    # the difference the section exists to express. The toggle overrides; it
    # does not set the baseline.
    treatment = request.args.get("tooling") or None
    if treatment not in (None, "amortized", "upfront"):
        treatment = None
    chosen_kinds = set(request.args.getlist("lever"))
    target = to_cents(request.args.get("target")) or item["target_unit_cents"]

    cards = []
    for strat in dr.strategies(item["id"]):
        card = dr.strategy_view(item, strat, costs, lane_rows, qty, mode, treatment)
        if card:
            # §E1.10 — a card is only highlighted against a target the client
            # set, and never on a figure with no provenance behind it.
            card["hits_target"] = bool(target and card["input_ids"]
                                       and card["landed_cents"] <= target)
            cards.append(card)

    # The "best today" figure and the levers are quoted against the cheapest
    # route, so they follow that strategy's treatment when none is forced.
    baseline = treatment or (cards[0]["treatment"] if cards else "amortized")
    base = dr.landed(costs, lane_rows, qty, mode,
                     amortize_tooling=(baseline == "amortized"))
    lever_rows = dr.lever_savings(item, costs, lane_rows, qty, mode, baseline, bounds)
    engineered = dr.engineered_price(item, costs, lane_rows, qty, mode, baseline,
                                     chosen_kinds, bounds)

    tooling = costs.get("tooling_total")
    return {
        "incomplete": False,
        "qty": qty, "bounds": bounds, "mode": mode, "treatment": treatment,
        "baseline_treatment": baseline,
        "target_cents": target, "chosen_kinds": chosen_kinds,
        "cards": cards,
        "current_landed_cents": base["landed_cents"] if base else None,
        "levers": lever_rows,
        "engineered": engineered,
        "freight_rows": dr.freight_comparison(costs, lane_rows, qty, treatment),
        "tooling_total_cents": tooling["value_cents"] if tooling else 0,
        "tooling_unit_cents": (tooling["value_cents"] / qty) if (tooling and qty) else 0,
        "lanes": lane_rows,
    }


@bp.route("/genome/<int:item_id>")
@client_required
def genome(item_id):
    """The manufacturing memory of an approved item (E.3).

    Reachable only for an item registered to this member — the check is
    `can_order`, the same one the order gate uses, so a genome cannot be read
    for a product that is not theirs.
    """
    if not catalogue.can_order(g.customer, item_id):
        abort(404)
    item = query("SELECT * FROM catalog_items WHERE id = ?", (item_id,), one=True)
    if item is None:
        abort(404)

    tools = genome_mod.tooling_facts(item_id, _cid())
    lines = []
    if tools:
        # The tooling section renders the §11.3 Tooling Line, not a second
        # description of the same tool (E3.02).
        qty = item["typical_moq"] or item["moq"] or 1
        landed = item["range_low_cents"] or 0
        lines = tooling.lines_for(item_id, _cid(), qty, landed, strategy="lowest_cost")

    return render_template(
        "portal/genome.html", item=item,
        sections=genome_mod.bodies(item_id),
        revisions=genome_mod.revisions(item_id),
        golden=genome_mod.golden_sample(item_id),
        quality=genome_mod.quality(item_id, _cid()),
        tooling_lines=lines,
        runs=genome_mod.runs(item_id),
        images=catalogue.item_images(item_id))


@bp.route("/membership")
@client_required
def membership_record():
    """The Factory Plan, both commitment columns, credits, and capacity (E.4)."""
    return render_template(
        "portal/membership.html",
        plan=genome_mod.factory_plan(_cid()),
        commitments=genome_mod.commitments(_cid()),
        credits=genome_mod.credits(_cid()),
        capacity=genome_mod.capacity(g.customer),
        weights=genome_mod.WEIGHTS,
        rules=genome_mod.FAIRNESS_RULES,
        boxes=genome_mod.boxes(_cid()),
        # CHG-024 — the acceptance record lives with the rest of the member's
        # record rather than on a page of its own. What a member agreed to, and
        # to which version of it, is part of the relationship, not a support
        # topic; the disclaimers page links here for the same reason.
        accepted=disc.acceptances_for(_cid()))


@bp.route("/products/<ref>/accept", methods=("POST",))
@client_required
@member_only
def product_accept(ref):
    """"Buy this route" — the strategy, quantity, freight mode and tooling
    treatment all travel into the order (E1.13).

    Snapshotted onto the order rather than referenced: a strategy edited on the
    desk afterwards must not silently change what someone already bought.
    """
    item = own_or_404(query("SELECT * FROM decision_items WHERE ref = ?", (ref,), one=True))
    if not item["published_at"]:
        abort(404)

    slot = to_int(request.form.get("slot"), 0)
    qty = to_int(request.form.get("qty"), 0)
    mode = request.form.get("mode") or "ocean"
    treatment = request.form.get("tooling") or "amortized"

    costs = dr.cost_inputs(item["id"])
    lane_rows = dr.lanes()
    strat = query("SELECT * FROM item_strategies WHERE item_id = ? AND slot = ?",
                  (item["id"], slot), one=True)
    bounds = dr.quantity_bounds(item)
    if strat is None or not costs or not lane_rows or not bounds:
        flash("That route is no longer available. Ask us and we will re-price it.", "error")
        return redirect(url_for("portal.products", ref=ref))

    qty = max(bounds["min"], min(bounds["max"], qty or bounds["min"]))
    card = dr.strategy_view(item, strat, costs, lane_rows, qty, mode, treatment)
    if card is None:
        flash("That route is no longer priceable.", "error")
        return redirect(url_for("portal.products", ref=ref))

    order = orders_mod.create_order(
        customer_id=_cid(),
        lines=[{"name": item["client_name"] or item["auto_name"],
                "sku": item["ref"],
                "unit_price_cents": int(round(card["landed_cents"])),
                "quantity": qty,
                "catalog_item_id": item["catalog_item_id"]}],
        actor=g.user["email"],
        notes=(f"{card['label']} — {card['title']}. {card['mode']} freight, "
               f"tooling {card['treatment']}, {qty:,} units."),
        destination=g.customer["country"],
    )
    return redirect(url_for("portal.checkout", order_id=order["id"]))


@bp.route("/products/<ref>/name", methods=("POST",))
@client_required
def product_rename(ref):
    """Their name for it. The internal ref never moves (E1.03)."""
    item = own_or_404(query("SELECT * FROM decision_items WHERE ref = ?", (ref,), one=True))
    name = (request.form.get("client_name") or "").strip()[:200]
    execute("UPDATE decision_items SET client_name = ? WHERE id = ?",
            (name or None, item["id"]))
    return redirect(url_for("portal.products", ref=ref))


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# the client ledger (PORT-06, §11.6)
#
# The member's own projection of the same record the admin bay reads. Scope is
# `_cid()` passed into every ledger call, so a cross-tenant fetch is not
# refused — it returns nothing, because the row was never in the query's reach.
#
# The totals are computed by `ledger.totals()`, the same function the admin
# ledger uses, over rows selected by the same filter. Two ledgers disagreeing
# about what a client paid is the worst inconsistency this product could ship
# (§11.6), and the way to prevent it is one implementation, not two that match.
# --------------------------------------------------------------------------
@bp.route("/ledger")
@client_required
def ledger_view():
    granularity = request.args.get("period", "month")
    if granularity not in ("month", "quarter", "year"):
        granularity = "month"
    start = (request.args.get("start") or "").strip() or None
    end = (request.args.get("end") or "").strip() or None
    order_ref = (request.args.get("order_ref") or "").strip() or None
    receipt_no = (request.args.get("receipt_no") or "").strip() or None

    found = ledger.search(customer_id=_cid(), start=start, end=end,
                          order_ref=order_ref, receipt_no=receipt_no)
    return render_template(
        "portal/ledger.html",
        rows=[ledger.client_row(r) for r in found["rows"]],
        found=found,
        period_view=ledger.periods(granularity, customer_id=_cid(), start=start, end=end),
        granularity=granularity,
        filters={"start": start, "end": end,
                 "order_ref": order_ref, "receipt_no": receipt_no},
        columns=ledger.CLIENT_COLUMNS)


@bp.route("/ledger/export.csv")
@client_required
def ledger_export():
    start = (request.args.get("start") or "").strip() or None
    end = (request.args.get("end") or "").strip() or None
    order_ref = (request.args.get("order_ref") or "").strip() or None
    receipt_no = (request.args.get("receipt_no") or "").strip() or None
    found = ledger.search(customer_id=_cid(), start=start, end=end,
                          order_ref=order_ref, receipt_no=receipt_no)
    columns, rows = ledger.to_export(found["rows"], client=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[c] for c in columns])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="my-ledger.csv"'})


@bp.route("/ledger/receipt/<receipt_no>")
@client_required
def ledger_receipt(receipt_no):
    # Scoped by customer inside the query: another member's receipt number does
    # not 403, it 404s, because it was never selectable.
    entry = ledger.receipt(receipt_no, customer_id=_cid())
    if entry is None:
        abort(404)
    return render_template("portal/receipt.html", entry=ledger.client_row(entry),
                           receipt_no=entry["receipt_no"])


@bp.route("/orders")
@client_required
def orders():
    rows = query("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC", (_cid(),))
    return render_template("portal/orders.html", orders=rows)


@bp.route("/purchases")
@client_required
def purchases():
    """Every item they have ever bought, newest first, with where each order stands."""
    rows = query(
        "SELECT oi.*, o.ref AS order_ref, o.id AS order_id, o.status AS order_status, "
        "o.created_at AS ordered_at, o.funds_confirmed_at, o.production_started_at, "
        "o.shipped_at, o.delivered_at, o.carrier, o.tracking_number, o.reviewed_at, o.updated_at "
        "FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "WHERE o.customer_id = ? AND o.status NOT IN ('PENDING_PAYMENT','CANCELLED') "
        "ORDER BY o.created_at DESC, oi.id", (_cid(),))
    totals = {
        # not "items" — Jinja resolves `.items` to the dict method, not the key
        "units": sum(r["quantity"] for r in rows),
        "spend": sum(r["line_total_cents"] for r in rows),
        "orders": len({r["order_id"] for r in rows}),
        "in_flight": len({r["order_id"] for r in rows
                          if r["order_status"] not in ("DELIVERED",)}),
    }
    reorderable = {}
    for r in rows:
        if r["catalog_item_id"] and catalog_mod.can_customer_see(g.customer, r["catalog_item_id"]):
            reorderable[r["id"]] = r["catalog_item_id"]
    return render_template("portal/purchases.html", rows=rows, totals=totals,
                           reorderable=reorderable)


@bp.route("/orders/<int:order_id>")
@client_required
def order_detail(order_id):
    order = own_or_404(orders_mod.get_order(order_id))
    items = orders_mod.get_items(order_id)
    events = query("SELECT * FROM order_events WHERE order_id = ? ORDER BY id DESC", (order_id,))
    state = orders_mod.review_state(order)
    return render_template("portal/order_detail.html", order=order, items=items,
                           events=events, state=state,
                           methods=payments.available_methods(),
                           estimate=orders_mod.freight_estimate(order),
                           freight_lines=_freight_lines(order))


@bp.route("/orders/<int:order_id>/checkout")
@client_required
@member_only
def checkout(order_id):
    """Our own checkout screen: what you're buying, and how you'd like to pay."""
    order = own_or_404(orders_mod.get_order(order_id))
    if order["payment_status"] == "PAID":
        return redirect(url_for("portal.order_detail", order_id=order_id))
    # Gate 3 of 3 (§8.4). The last point before money moves. An order can sit
    # unpaid for days, so the registration is checked again here rather than
    # inherited from whatever was true when the order was created.
    blocked = _unregistered_lines(order_id)
    if blocked:
        flash("This order can't be paid: " + ", ".join(blocked)
              + " is no longer registered to your account.", "error")
        return redirect(url_for("portal.order_detail", order_id=order_id))
    net = orders_mod.net_before_processing(order)
    return render_template("portal/checkout.html", order=order,
                           items=orders_mod.get_items(order_id),
                           methods=payments.available_methods(),
                           options=orders_mod.quote_payment_options(net),
                           estimate=orders_mod.freight_estimate(order),
                           freight_lines=_freight_lines(order),
                           disclaimers=disc.current())


@bp.route("/orders/<int:order_id>/pay", methods=("POST",))
@client_required
@member_only
def pay(order_id):
    order = own_or_404(orders_mod.get_order(order_id))
    if order["payment_status"] == "PAID":
        flash("This order is already paid.", "ok")
        return redirect(url_for("portal.order_detail", order_id=order_id))
    blocked = _unregistered_lines(order_id)
    if blocked:
        flash("This order can't be paid: " + ", ".join(blocked)
              + " is no longer registered to your account.", "error")
        return redirect(url_for("portal.order_detail", order_id=order_id))
    # CHG-024 — acceptance is recorded before money moves, and it records the
    # exact version. A boolean on the order would say a box was ticked; it would
    # not say what the words were, and the words change. Refusing here rather
    # than at render time means a form replayed without the field cannot pay.
    live = disc.current()
    if live:
        if not request.form.get("accept_disclaimers"):
            flash("Please read and accept the disclaimers before paying.", "error")
            return redirect(url_for("portal.checkout", order_id=order_id))
        disc.accept([d["slug"] for d in live],
                    actor_email=g.user["email"],
                    customer_id=order["customer_id"],
                    user_id=g.user["id"],
                    order_ref=order["ref"],
                    ip_hint=(request.headers.get("X-Forwarded-For")
                             or request.remote_addr or "")[:45])

    items = orders_mod.get_items(order_id)
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    method = request.form.get("method")
    if method not in payments.available_methods():
        method = None
    # Price the network's cut for the method they actually chose, then charge that.
    orders_mod.recalc_totals(order_id, method=method)
    execute("UPDATE orders SET payment_method = ? WHERE id = ?",
            ("ACH" if method == "us_bank_account" else "CARD", order_id))
    order = orders_mod.get_order(order_id)
    try:
        session = payments.create_checkout_session(order, items, customer, method=method)
    except payments.PaymentError as exc:
        current_app.logger.error("Checkout failed for %s: %s", order["ref"], exc)
        flash(f"We couldn't start checkout: {exc}", "error")
        return redirect(url_for("portal.order_detail", order_id=order_id))
    execute(
        "UPDATE orders SET checkout_session_id = ?, payment_provider = ?, updated_at = ? WHERE id = ?",
        (session["id"], session["provider"], now_str(), order_id))
    orders_mod.log_event(order_id, "CHECKOUT_STARTED",
                         f"{session['provider']} session {session['id']}", g.user["email"])
    return redirect(session["url"])


@bp.route("/checkout/return/<ref>")
@client_required
def checkout_return(ref):
    order = own_or_404(orders_mod.get_order(ref=ref))
    result = request.args.get("result")
    if result == "cancel":
        flash("Checkout cancelled — nothing was charged.", "error")
        return redirect(url_for("portal.order_detail", order_id=order["id"]))

    # Stripe's webhook is the source of truth; this is the optimistic UI path.
    session_id = request.args.get("session_id")
    if session_id and current_app.config["PAYMENT_PROVIDER"] == "stripe":
        try:
            session = payments.retrieve_session(session_id)
            status = session.get("payment_status")
            method = payments.method_from_stripe(session)
            if status == "paid":
                orders_mod.confirm_funds(order["id"], method=method,
                                         payment_ref=session.get("payment_intent"),
                                         provider="stripe", actor="checkout_return")
            elif status in ("unpaid", "no_payment_required") or session.get("status") == "open":
                orders_mod.mark_processing(order["id"], method=method,
                                           payment_ref=session.get("payment_intent"),
                                           provider="stripe")
        except Exception as exc:  # noqa: BLE001
            current_app.logger.warning("Could not read Stripe session %s: %s", session_id, exc)

    order = orders_mod.get_order(order["id"])
    return render_template("portal/checkout_complete.html", order=order,
                           items=orders_mod.get_items(order["id"]),
                           state=orders_mod.review_state(order))


# --------------------------------------------------------------------------
# mock bank (development only — PAYMENT_PROVIDER=mock)
# --------------------------------------------------------------------------
@bp.route("/checkout/simulate/<ref>", methods=("GET", "POST"))
@client_required
def mock_bank(ref):
    if current_app.config["PAYMENT_PROVIDER"] == "stripe":
        abort(404)
    order = own_or_404(orders_mod.get_order(ref=ref))
    items = orders_mod.get_items(order["id"])
    if request.method == "POST":
        method = request.form.get("method", "CARD")
        outcome = request.form.get("outcome", "success")
        if outcome == "fail":
            orders_mod.fail_payment(order["id"], "Simulated decline", actor=g.user["email"])
            flash("Payment declined (simulated).", "error")
            return redirect(url_for("portal.order_detail", order_id=order["id"]))
        if method == "ACH" and request.form.get("settle") != "now":
            orders_mod.mark_processing(order["id"], method="ACH",
                                       payment_ref=f"mock_ach_{order['ref']}", provider="mock")
            flash("ACH debit initiated. Funds typically settle in 1–3 business days.", "ok")
        else:
            orders_mod.confirm_funds(order["id"], method=method,
                                     payment_ref=f"mock_{method.lower()}_{order['ref']}",
                                     provider="mock", actor=g.user["email"])
        return redirect(url_for("portal.checkout_return", ref=order["ref"], result="success"))
    preset = request.args.get("method") or ""
    return render_template("portal/mock_bank.html", order=order, items=items,
                           methods=payments.available_methods(), preset=preset)
