"""Member portal — sealed per customer.

Every query in this module is scoped by `g.user['customer_id']`, and anything
fetched by id is passed through `own_or_404`. There is no route here that can
return another customer's row.

Browsing and quoting are open to any account with a login. Anything that spends
money is wrapped in `member_only` — acceptance is what unlocks buying.
"""
import functools
from pathlib import Path

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template,
    request, send_from_directory, url_for,
)

from .. import catalog as catalog_mod
from .. import catalogue
from .. import membership
from .. import orders as orders_mod
from .. import payments
from ..auth import client_required, own_or_404
from ..db import execute, query
from ..utils import money, now_str, to_int

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
    return render_template("portal/quotes.html", quotes=rows, estimates=estimates, status=status)


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
    return render_template("portal/catalog_item.html", item=match[0])


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
                           freight_lines=_freight_lines(order))


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
