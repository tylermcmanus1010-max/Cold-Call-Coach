"""Payments.

Two providers behind one interface:

  stripe — real Stripe Checkout over the REST API (no SDK required, just
           form-encoded POSTs). Cards + ACH bank debit in one session.
           Webhook signatures verified with HMAC-SHA256, same algorithm the
           official library uses.
  mock   — an in-app simulated bank for local development and demos. Same
           state machine, including the delayed-settlement behaviour that
           makes ACH different from cards.

The critical business rule lives in `confirm_funds` (orders.py), not here:
money confirmed -> 24h manufacturer review -> only then can it ship.
"""
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

from flask import current_app, url_for

STRIPE_API = "https://api.stripe.com/v1"


class PaymentError(Exception):
    pass


# --------------------------------------------------------------------------
# low-level Stripe transport
# --------------------------------------------------------------------------
def _stripe_post(path: str, params: dict) -> dict:
    key = current_app.config["STRIPE_SECRET_KEY"]
    if not key:
        raise PaymentError("STRIPE_SECRET_KEY is not configured.")
    data = urllib.parse.urlencode(_flatten(params), doseq=True).encode()
    req = urllib.request.Request(
        f"{STRIPE_API}/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Stripe-Version": "2024-06-20",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        current_app.logger.error("Stripe error %s: %s", exc.code, body)
        try:
            message = json.loads(body)["error"]["message"]
        except Exception:  # noqa: BLE001
            message = body[:300]
        raise PaymentError(message) from exc
    except Exception as exc:  # noqa: BLE001
        raise PaymentError(str(exc)) from exc


def _flatten(params, parent=None, out=None):
    """Turn nested dicts/lists into Stripe's bracket notation."""
    out = {} if out is None else out
    for key, value in params.items():
        full = f"{parent}[{key}]" if parent else key
        if isinstance(value, dict):
            _flatten(value, full, out)
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    _flatten(item, f"{full}[{i}]", out)
                else:
                    out[f"{full}[{i}]"] = item
        elif value is not None:
            out[full] = value
    return out


# --------------------------------------------------------------------------
# public interface
# --------------------------------------------------------------------------
def available_methods() -> list:
    cfg = current_app.config
    methods = []
    if cfg["ENABLE_CARD"]:
        methods.append("card")
    if cfg["ENABLE_ACH"]:
        methods.append("us_bank_account")
    return methods or ["card"]


def create_checkout_session(order, items, customer, method=None) -> dict:
    """Returns {'url': ..., 'id': ..., 'provider': ...}.

    `method` is 'card' or 'us_bank_account' when the member has already chosen on
    our own checkout screen — Stripe then offers only that one, so the page they
    land on matches the button they pressed.
    """
    provider = current_app.config["PAYMENT_PROVIDER"]
    success = url_for("portal.checkout_return", ref=order["ref"], result="success", _external=True)
    cancel = url_for("portal.checkout_return", ref=order["ref"], result="cancel", _external=True)

    allowed = available_methods()
    chosen = [method] if method in allowed else allowed

    if provider != "stripe":
        return {
            "provider": "mock",
            "id": f"cs_mock_{order['ref']}",
            "url": url_for("portal.mock_bank", ref=order["ref"], method=method or ""),
        }

    line_items = [
        {
            "price_data": {
                "currency": order["currency"],
                "unit_amount": int(it["unit_price_cents"]),
                "product_data": {
                    "name": it["name"][:250],
                    "description": (it["sku"] or "Custom manufacturing")[:250],
                },
            },
            "quantity": int(it["quantity"]),
        }
        for it in items
    ]
    if order["shipping_cents"]:
        line_items.append({
            "price_data": {
                "currency": order["currency"],
                "unit_amount": int(order["shipping_cents"]),
                "product_data": {"name": "Freight & duties"},
            },
            "quantity": 1,
        })
    fee = int(order["fee_cents"] or 0)
    if fee:
        pct = current_app.config["PURCHASE_FEE_PERCENT"]
        line_items.append({
            "price_data": {
                "currency": order["currency"],
                "unit_amount": fee,
                "product_data": {"name": f"{current_app.config['FEE_LABEL']} ({pct:g}%)"},
            },
            "quantity": 1,
        })
    processing = int(order["processing_fee_cents"] or 0)
    if processing:
        line_items.append({
            "price_data": {
                "currency": order["currency"],
                "unit_amount": processing,
                "product_data": {
                    "name": "Payment processing",
                    "description": "Charged by Stripe and passed on at cost.",
                },
            },
            "quantity": 1,
        })

    payload = {
        "mode": "payment",
        "success_url": success + "&session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": cancel,
        "client_reference_id": order["ref"],
        "customer_email": customer["email"],
        "line_items": line_items,
        "payment_method_types": chosen,
        "payment_intent_data": {
            "description": f"{current_app.config['COMPANY_NAME']} order {order['ref']}",
            "metadata": {"order_ref": order["ref"], "order_id": order["id"]},
        },
        "metadata": {"order_ref": order["ref"], "order_id": order["id"]},
    }
    session = _stripe_post("checkout/sessions", payload)
    return {"provider": "stripe", "id": session["id"], "url": session["url"]}


def retrieve_session(session_id: str) -> dict:
    key = current_app.config["STRIPE_SECRET_KEY"]
    req = urllib.request.Request(
        f"{STRIPE_API}/checkout/sessions/{session_id}",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def verify_webhook(payload: bytes, sig_header: str, tolerance: int = 300) -> dict:
    """Verify a Stripe webhook signature (same scheme as stripe.Webhook.construct_event)."""
    secret = current_app.config["STRIPE_WEBHOOK_SECRET"]
    if not secret:
        raise PaymentError("STRIPE_WEBHOOK_SECRET is not configured.")
    if not sig_header:
        raise PaymentError("Missing Stripe-Signature header.")

    parts = dict(
        piece.split("=", 1) for piece in sig_header.split(",") if "=" in piece
    )
    timestamp = parts.get("t")
    signatures = [v for k, v in
                  (p.split("=", 1) for p in sig_header.split(",") if "=" in p) if k == "v1"]
    if not timestamp or not signatures:
        raise PaymentError("Malformed Stripe-Signature header.")
    if abs(time.time() - int(timestamp)) > tolerance:
        raise PaymentError("Webhook timestamp outside tolerance.")

    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise PaymentError("Webhook signature mismatch.")
    return json.loads(payload.decode())


def method_from_stripe(session: dict) -> str:
    types = session.get("payment_method_types") or []
    details = ((session.get("payment_intent") or {}) if isinstance(session.get("payment_intent"), dict) else {})
    if "us_bank_account" in types and len(types) == 1:
        return "ACH"
    charges = (details.get("charges") or {}).get("data") or []
    if charges:
        pmt = (charges[0].get("payment_method_details") or {})
        if "us_bank_account" in pmt:
            return "ACH"
        if "card" in pmt:
            return "CARD"
    return "CARD"
