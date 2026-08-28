"""Order lifecycle — the spine of the business.

    PENDING_PAYMENT
        -> PAYMENT_PROCESSING   (ACH initiated, money not settled yet)
        -> IN_REVIEW            (funds confirmed; 24h manufacturer review starts)
        -> APPROVED             (manufacturer signed off; review window closed)
        -> IN_PRODUCTION -> SHIPPED -> DELIVERED

Two rules are enforced in code, not convention:
  1. An order can never reach SHIPPED without a completed manufacturer review.
  2. The centralized orders inbox is emailed exactly once, at the moment funds
     are confirmed — never on an unpaid or merely-initiated payment.
"""
import json

from flask import current_app

from . import freight, mail
from .db import execute, query
from .utils import money, now_str, plus_hours, pretty_dt


def log_event(order_id, event, detail=None, actor="system"):
    execute(
        "INSERT INTO order_events (order_id, event, detail, actor) VALUES (?, ?, ?, ?)",
        (order_id, event, detail, actor),
    )


def get_order(order_id=None, ref=None):
    if ref:
        return query("SELECT * FROM orders WHERE ref = ?", (ref,), one=True)
    return query("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)


def get_items(order_id):
    return query("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,))


def fee_on(amount_cents):
    """Our convenience fee, rounded to the cent."""
    pct = current_app.config["PURCHASE_FEE_PERCENT"]
    if not pct:
        return 0
    return int(round(amount_cents * pct / 100.0))


def processing_fee_for(net_cents, method):
    """What the payment network takes, grossed up so `net_cents` actually lands.

    Stripe charges on the amount the customer pays, so charging them a flat 2.9%
    of the subtotal would leave us short. Solving T = (N + fixed) / (1 - rate)
    gives the amount to charge; the fee we quote is the difference. That way the
    number on the invoice is exactly what Stripe deducts — no rounding in our
    favour, which is also what surcharging rules require.
    """
    cfg = current_app.config
    if not cfg["PASS_THROUGH_PROCESSING"] or not net_cents:
        return 0
    if method in ("us_bank_account", "ACH"):
        rate = cfg["STRIPE_ACH_PERCENT"] / 100.0
        cap = cfg["STRIPE_ACH_CAP_CENTS"]
        gross = net_cents / (1 - rate) if rate < 1 else net_cents
        fee = int(round(gross - net_cents))
        return min(fee, cap)
    if method in ("WIRE", "CHECK", "manual"):
        return 0                      # they pay their own bank; nothing for us to pass on
    rate = cfg["STRIPE_CARD_PERCENT"] / 100.0
    fixed = cfg["STRIPE_CARD_FIXED_CENTS"]
    gross = (net_cents + fixed) / (1 - rate) if rate < 1 else net_cents + fixed
    return int(round(gross - net_cents))


def quote_payment_options(net_cents):
    """Both payment methods priced side by side, so the choice is informed."""
    cfg = current_app.config
    out = []
    if cfg["ENABLE_CARD"]:
        fee = processing_fee_for(net_cents, "card")
        out.append({"key": "card", "label": "Card", "fee": fee, "total": net_cents + fee,
                    "note": f"{cfg['STRIPE_CARD_PERCENT']:g}% + "
                            f"{cfg['STRIPE_CARD_FIXED_CENTS']}¢ charged by Stripe"})
    if cfg["ENABLE_ACH"]:
        fee = processing_fee_for(net_cents, "us_bank_account")
        out.append({"key": "us_bank_account", "label": "Bank transfer (ACH)", "fee": fee,
                    "total": net_cents + fee,
                    "note": f"{cfg['STRIPE_ACH_PERCENT']:g}% capped at "
                            f"${cfg['STRIPE_ACH_CAP_CENTS'] / 100:.2f} charged by Stripe"})
    return out


def net_before_processing(order):
    """Everything except the payment network's cut."""
    return ((order["subtotal_cents"] or 0) + (order["shipping_cents"] or 0)
            + (order["tax_cents"] or 0) + (order["fee_cents"] or 0))


def recalc_totals(order_id, method=None):
    """The single source of truth for an order's money.

        goods
      + freight & customs   (zero when the owner has waived it)
      + tax
      + convenience fee     1.5% of the above
      + processing fee      what the network takes, at cost
      = total
    """
    row = query(
        "SELECT COALESCE(SUM(line_total_cents), 0) AS subtotal FROM order_items WHERE order_id = ?",
        (order_id,), one=True,
    )
    order = get_order(order_id)
    subtotal = row["subtotal"]
    # `shipping_cents` is what the freight *costs* and is never zeroed — the waiver
    # is a separate flag, so taking the offer back restores the real figure rather
    # than losing it.
    charged_shipping = 0 if order["freight_waived"] else (order["shipping_cents"] or 0)
    before_fee = subtotal + charged_shipping + (order["tax_cents"] or 0)
    fee = fee_on(before_fee)
    net = before_fee + fee
    method = method or order["payment_method"]
    processing = processing_fee_for(net, method) if method else 0
    total = net + processing
    execute(
        "UPDATE orders SET subtotal_cents = ?, fee_cents = ?, "
        "processing_fee_cents = ?, total_cents = ?, updated_at = ? WHERE id = ?",
        (subtotal, fee, processing, total, now_str(), order_id),
    )
    return total


def charged_shipping(order):
    """What the client actually pays for freight — zero when the owner absorbs it."""
    return 0 if order["freight_waived"] else (order["shipping_cents"] or 0)


def attach_freight_estimate(order_id, category=None, destination=None, mode="SEA",
                            quantity=None):
    """Work out what freight and customs would cost, and store the whole breakdown.

    The figure is shown to the client — struck through when we absorb it — so it
    has to be a real estimate we can defend line by line, not a number chosen to
    make the gesture look larger.
    """
    order = get_order(order_id)
    items = get_items(order_id)
    qty = quantity or sum(i["quantity"] for i in items) or 1
    est = freight.estimate(
        declared_value_cents=order["subtotal_cents"], quantity=qty,
        category=category, destination=destination, mode=mode)
    execute(
        "UPDATE orders SET freight_estimate_cents = ?, customs_estimate_cents = ?, "
        "freight_breakdown = ?, shipping_cents = ?, updated_at = ? WHERE id = ?",
        (est["freight_total_cents"], est["customs_total_cents"], json.dumps(est),
         est["grand_total_cents"], now_str(), order_id))
    recalc_totals(order_id)
    return est


def freight_estimate(order):
    """The stored breakdown, or None."""
    raw = order["freight_breakdown"] if "freight_breakdown" in order.keys() else None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def set_freight_waived(order_id, waived, actor, note=None):
    """The owner absorbs freight and customs on this order (or takes it back)."""
    execute(
        "UPDATE orders SET freight_waived = ?, waived_by = ?, waived_at = ?, updated_at = ? "
        "WHERE id = ?",
        (1 if waived else 0, actor if waived else None, now_str() if waived else None,
         now_str(), order_id))
    if waived:
        est = get_order(order_id)
        log_event(order_id, "FREIGHT_WAIVED",
                  f"Freight and customs absorbed by the owner "
                  f"({money(est['freight_estimate_cents'] + est['customs_estimate_cents'])})"
                  + (f" — {note}" if note else ""), actor)
    else:
        log_event(order_id, "FREIGHT_REINSTATED", note, actor)
    recalc_totals(order_id)
    return get_order(order_id)


# --------------------------------------------------------------------------
# creation
# --------------------------------------------------------------------------
def create_order(customer_id, lines, shipping_cents=0, tax_cents=0,
                 source_quote_id=None, ship_to=None, notes=None, actor="client",
                 category=None, destination=None, ship_mode="SEA"):
    """`lines` = [{name, sku, unit_price_cents, quantity, catalog_item_id, quote_id}]"""
    from .db import next_ref
    ref = next_ref("MMI-O", "orders", start=2001)
    order_id = execute(
        "INSERT INTO orders (ref, customer_id, source_quote_id, status, shipping_cents, "
        "tax_cents, ship_to, notes) VALUES (?, ?, ?, 'PENDING_PAYMENT', ?, ?, ?, ?)",
        (ref, customer_id, source_quote_id, shipping_cents, tax_cents, ship_to, notes),
    )
    for line in lines:
        qty = int(line.get("quantity") or 1)
        unit = int(line.get("unit_price_cents") or 0)
        execute(
            "INSERT INTO order_items (order_id, catalog_item_id, quote_id, name, sku, "
            "unit_price_cents, quantity, line_total_cents) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, line.get("catalog_item_id"), line.get("quote_id"), line["name"],
             line.get("sku"), unit, qty, unit * qty),
        )
    customer = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    recalc_totals(order_id)

    # Price the freight and customs this order would carry, then apply the owner's
    # standing offer for this account if there is one.
    attach_freight_estimate(order_id, category=category, destination=destination or
                            (customer["country"] if customer else None), mode=ship_mode)
    try:
        default_waived = customer["freight_waived_default"]
    except (IndexError, KeyError):
        default_waived = 0
    if default_waived:
        set_freight_waived(order_id, True, "Owner standing offer",
                           f"Standing offer on {customer['ref']}")

    log_event(order_id, "ORDER_CREATED", f"{len(lines)} line item(s)", actor)
    return get_order(order_id)


# --------------------------------------------------------------------------
# payment transitions
# --------------------------------------------------------------------------
def mark_processing(order_id, method="ACH", payment_ref=None, provider=None):
    """ACH initiated. Money is in flight but NOT confirmed — nothing downstream fires."""
    execute(
        "UPDATE orders SET status = 'PAYMENT_PROCESSING', payment_status = 'PROCESSING', "
        "payment_method = ?, payment_ref = COALESCE(?, payment_ref), "
        "payment_provider = COALESCE(?, payment_provider), updated_at = ? WHERE id = ?",
        (method, payment_ref, provider, now_str(), order_id),
    )
    log_event(order_id, "PAYMENT_INITIATED",
              f"{method} payment initiated; awaiting settlement", "payments")
    return get_order(order_id)


def confirm_funds(order_id, method="CARD", payment_ref=None, provider=None, actor="payments"):
    """Funds confirmed. Starts the 24h manufacturer review and fires the orders email.

    Idempotent: a duplicate webhook will not double-send or restart the clock.
    """
    order = get_order(order_id)
    if order is None:
        return None
    if order["payment_status"] == "PAID" and order["funds_confirmed_at"]:
        return order  # already handled

    hours = current_app.config["ORDER_REVIEW_HOURS"]
    confirmed = now_str()
    release = plus_hours(hours)
    execute(
        "UPDATE orders SET status = 'IN_REVIEW', payment_status = 'PAID', payment_method = ?, "
        "payment_ref = COALESCE(?, payment_ref), payment_provider = COALESCE(?, payment_provider), "
        "funds_confirmed_at = ?, review_release_at = ?, updated_at = ? WHERE id = ?",
        (method, payment_ref, provider, confirmed, release, confirmed, order_id),
    )
    log_event(order_id, "FUNDS_CONFIRMED",
              f"{method} funds confirmed — {hours}h manufacturer review opened", actor)

    order = get_order(order_id)
    _notify_funds_confirmed(order)

    # Put the review deadline on the admin calendar so it can't be forgotten.
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    execute(
        "INSERT INTO calendar_events (title, customer_id, order_id, kind, starts_at, notes, created_by) "
        "VALUES (?, ?, ?, 'DEADLINE', ?, ?, 'system')",
        (f"Review deadline · {order['ref']}", order["customer_id"], order["id"], release,
         f"{hours}h manufacturer review for {customer['company_name']} closes now."),
    )
    _bump_lifetime_value(order)
    return order


def fail_payment(order_id, reason="Payment failed", actor="payments"):
    execute(
        "UPDATE orders SET status = 'PENDING_PAYMENT', payment_status = 'FAILED', updated_at = ? "
        "WHERE id = ?", (now_str(), order_id),
    )
    log_event(order_id, "PAYMENT_FAILED", reason, actor)
    return get_order(order_id)


def _bump_lifetime_value(order):
    execute(
        "UPDATE customers SET lifetime_value_cents = lifetime_value_cents + ?, "
        "stage = CASE WHEN stage IN ('LEAD','QUOTING','NEGOTIATING') THEN 'ACTIVE' ELSE stage END, "
        "updated_at = ? WHERE id = ?",
        (order["total_cents"], now_str(), order["customer_id"]),
    )


# --------------------------------------------------------------------------
# manufacturer review gate
# --------------------------------------------------------------------------
def review_state(order):
    """What the 24h gate says about this order right now."""
    from .utils import countdown, parse, utcnow
    if not order["funds_confirmed_at"]:
        return {"phase": "awaiting_funds", "can_ship": False, "countdown": None}
    if order["reviewed_at"]:
        return {"phase": "reviewed", "can_ship": order["status"] not in
                ("ON_HOLD", "CANCELLED", "REFUNDED"), "countdown": None}
    cd = countdown(order["review_release_at"])
    elapsed = cd["overdue"]
    return {
        "phase": "elapsed" if elapsed else "in_review",
        "can_ship": False,
        "countdown": cd,
    }


def approve_review(order_id, actor, notes=None, start_production=True):
    order = get_order(order_id)
    if order["payment_status"] != "PAID":
        raise ValueError("Cannot release an order whose funds are not confirmed.")
    status = "IN_PRODUCTION" if start_production else "APPROVED"
    execute(
        "UPDATE orders SET status = ?, reviewed_at = ?, reviewed_by = ?, review_notes = ?, "
        "production_started_at = CASE WHEN ? = 'IN_PRODUCTION' THEN ? ELSE production_started_at END, "
        "updated_at = ? WHERE id = ?",
        (status, now_str(), actor, notes, status, now_str(), now_str(), order_id),
    )
    log_event(order_id, "REVIEW_APPROVED", notes or "Manufacturer review passed", actor)
    order = get_order(order_id)
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    mail.send(
        customer["email"],
        f"{order['ref']} approved for production",
        template="order_approved",
        order=order, customer=customer, items=get_items(order_id),
        company=current_app.config["COMPANY_NAME"], money=money, pretty_dt=pretty_dt,
        site_url=current_app.config["SITE_URL"],
    )
    return order


def hold_order(order_id, actor, reason):
    execute(
        "UPDATE orders SET status = 'ON_HOLD', review_notes = ?, reviewed_at = ?, reviewed_by = ?, "
        "updated_at = ? WHERE id = ?", (reason, now_str(), actor, now_str(), order_id),
    )
    log_event(order_id, "ORDER_HELD", reason, actor)
    order = get_order(order_id)
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    mail.send(
        customer["email"], f"{order['ref']} is on hold", template="order_held",
        order=order, customer=customer, reason=reason,
        company=current_app.config["COMPANY_NAME"], site_url=current_app.config["SITE_URL"],
    )
    return order


def ship_order(order_id, actor, carrier=None, tracking=None):
    order = get_order(order_id)
    state = review_state(order)
    if not state["can_ship"]:
        raise ValueError(
            "This order has not cleared the manufacturer review window — it cannot ship yet."
        )
    execute(
        "UPDATE orders SET status = 'SHIPPED', shipped_at = ?, carrier = ?, tracking_number = ?, "
        "updated_at = ? WHERE id = ?", (now_str(), carrier, tracking, now_str(), order_id),
    )
    log_event(order_id, "SHIPPED", f"{carrier or 'Carrier'} {tracking or ''}".strip(), actor)
    order = get_order(order_id)
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    mail.send(
        customer["email"], f"{order['ref']} has shipped", template="order_shipped",
        order=order, customer=customer, items=get_items(order_id),
        company=current_app.config["COMPANY_NAME"], money=money, pretty_dt=pretty_dt,
        site_url=current_app.config["SITE_URL"],
    )
    mail.send(
        current_app.config["ORDERS_EMAIL"], f"[SHIPPED] {order['ref']} · {customer['company_name']}",
        template="order_shipped", order=order, customer=customer, items=get_items(order_id),
        company=current_app.config["COMPANY_NAME"], money=money, pretty_dt=pretty_dt,
        site_url=current_app.config["SITE_URL"],
    )
    return order


# --------------------------------------------------------------------------
# notifications
# --------------------------------------------------------------------------
def _notify_funds_confirmed(order):
    cfg = current_app.config
    customer = query("SELECT * FROM customers WHERE id = ?", (order["customer_id"],), one=True)
    items = get_items(order["id"])

    # 1. the centralized orders inbox — the trigger the whole shop works from
    mail.send(
        cfg["ORDERS_EMAIL"],
        f"[NEW ORDER · FUNDS CONFIRMED] {order['ref']} · {customer['company_name']} · {money(order['total_cents'])}",
        template="order_internal",
        order=order, customer=customer, items=items,
        company=cfg["COMPANY_NAME"], money=money, pretty_dt=pretty_dt,
        review_hours=cfg["ORDER_REVIEW_HOURS"], site_url=cfg["SITE_URL"],
        fee_label=cfg["FEE_LABEL"], fee_percent=f"{cfg['PURCHASE_FEE_PERCENT']:g}",
    )
    # 2. the client's receipt
    mail.send(
        customer["email"],
        f"Payment confirmed · {order['ref']}",
        template="order_receipt",
        order=order, customer=customer, items=items,
        company=cfg["COMPANY_NAME"], money=money, pretty_dt=pretty_dt,
        review_hours=cfg["ORDER_REVIEW_HOURS"], site_url=cfg["SITE_URL"],
        fee_label=cfg["FEE_LABEL"], fee_percent=f"{cfg['PURCHASE_FEE_PERCENT']:g}",
    )
    execute("UPDATE orders SET orders_email_sent_at = ? WHERE id = ?", (now_str(), order["id"]))
    log_event(order["id"], "ORDERS_EMAIL_SENT", f"Sent to {cfg['ORDERS_EMAIL']}", "system")
