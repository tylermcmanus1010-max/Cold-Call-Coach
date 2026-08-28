"""Payment webhooks — the authoritative source of payment truth.

Stripe posts here. The endpoint is idempotent (webhook_log has a unique index
on provider+event_id) so retries and duplicate deliveries are harmless.
"""
import json

from flask import Blueprint, current_app, request

from .. import orders as orders_mod
from .. import payments
from ..db import execute, query

bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


@bp.route("/stripe", methods=("POST",))
def stripe():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = payments.verify_webhook(payload, sig)
    except payments.PaymentError as exc:
        current_app.logger.warning("Rejected Stripe webhook: %s", exc)
        return {"error": str(exc)}, 400

    event_id = event.get("id")
    if query("SELECT id FROM webhook_log WHERE provider = 'stripe' AND event_id = ?",
             (event_id,), one=True):
        return {"received": True, "duplicate": True}, 200

    execute(
        "INSERT INTO webhook_log (provider, event_id, event_type, payload) VALUES ('stripe', ?, ?, ?)",
        (event_id, event.get("type"), json.dumps(event)[:20000]))

    obj = (event.get("data") or {}).get("object") or {}
    ref = (obj.get("metadata") or {}).get("order_ref") or obj.get("client_reference_id")
    order = orders_mod.get_order(ref=ref) if ref else None
    note = "no matching order"

    if order:
        etype = event.get("type")
        if etype == "checkout.session.completed":
            if obj.get("payment_status") == "paid":
                orders_mod.confirm_funds(order["id"], method=payments.method_from_stripe(obj),
                                         payment_ref=obj.get("payment_intent"), provider="stripe")
                note = "funds confirmed"
            else:
                # ACH: the debit is initiated but has not settled. Nothing downstream fires.
                orders_mod.mark_processing(order["id"], method="ACH",
                                           payment_ref=obj.get("payment_intent"), provider="stripe")
                note = "payment processing (awaiting settlement)"
        elif etype == "checkout.session.async_payment_succeeded":
            orders_mod.confirm_funds(order["id"], method="ACH",
                                     payment_ref=obj.get("payment_intent"), provider="stripe")
            note = "ACH settled — funds confirmed"
        elif etype in ("checkout.session.async_payment_failed", "payment_intent.payment_failed"):
            orders_mod.fail_payment(order["id"], "Stripe reported the payment failed")
            note = "payment failed"
        elif etype == "charge.refunded":
            execute("UPDATE orders SET status = 'REFUNDED', payment_status = 'REFUNDED' WHERE id = ?",
                    (order["id"],))
            orders_mod.log_event(order["id"], "REFUNDED", "Stripe refund", "stripe")
            note = "refunded"
        else:
            note = f"ignored event {etype}"

    execute("UPDATE webhook_log SET handled = 1, note = ? WHERE provider = 'stripe' AND event_id = ?",
            (note, event_id))
    return {"received": True}, 200
