"""Configuration for Monti Makes It.

Everything is driven by environment variables so the same code runs
locally, on a staging box, and in production. See .env.example.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # --- core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # --- demo doors -------------------------------------------------------
    # Off unless something sets it, and it must stay off in production.
    #
    # The demo signs you straight into Boars Head's portal and into the admin
    # portal without a password. Boars Head is a real account with real orders,
    # real negotiated prices and a real ledger, and the admin portal reaches
    # every account there is — so with this on, the front page is a way in for
    # anyone who reads it.
    #
    # It exists because reviewing the build means clicking into both portals a
    # hundred times, and typing a generated password each time is friction that
    # buys nothing on a laptop. It buys a great deal on a public host, which is
    # why the doors do not exist at all unless this is set: the routes 404 and
    # the buttons are not rendered. A43 proves both.
    DEMO_MODE = _bool("DEMO_MODE", False)
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "monti.db"))
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "monti" / "static" / "uploads"))
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 25) * 1024 * 1024
    ALLOWED_UPLOAD_EXT = {
        ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
        ".step", ".stp", ".stl", ".dxf", ".dwg", ".ai", ".psd",
        ".zip", ".xlsx", ".xls", ".csv", ".docx", ".txt",
    }

    # --- company identity ---
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Monti Makes It")
    COMPANY_TAGLINE = os.environ.get(
        "COMPANY_TAGLINE", "Send us the thing. We'll tell you what it costs to make it."
    )
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000")
    SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "hello@montimakesit.com")

    # --- the centralized orders inbox ---
    ORDERS_EMAIL = os.environ.get("ORDERS_EMAIL", "orders@montimakesit.com")
    QUOTES_EMAIL = os.environ.get("QUOTES_EMAIL", "quotes@montimakesit.com")
    APPLICATIONS_EMAIL = os.environ.get("APPLICATIONS_EMAIL", "membership@montimakesit.com")

    # --- SLAs ---
    QUOTE_SLA_HOURS = _int("QUOTE_SLA_HOURS", 24)
    ORDER_REVIEW_HOURS = _int("ORDER_REVIEW_HOURS", 24)

    # --- membership ---
    QUOTE_LIMIT = _int("QUOTE_LIMIT", 10)          # new quotes per member per cycle
    QUOTE_CYCLE_DAYS = _int("QUOTE_CYCLE_DAYS", 30)
    INTERVIEW_LINK = os.environ.get("INTERVIEW_LINK", "")  # your standing Zoom room, optional

    # --- email ---
    MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "log")  # log | smtp
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _bool("SMTP_USE_TLS", True)
    MAIL_FROM = os.environ.get("MAIL_FROM", "Monti Makes It <no-reply@montimakesit.com>")

    # --- fees ---
    # One fee, on everything, and nothing else. Expressed as a percentage of the
    # order value (goods + freight + tax).
    PURCHASE_FEE_PERCENT = float(os.environ.get("PURCHASE_FEE_PERCENT", "1.5"))
    FEE_LABEL = os.environ.get("FEE_LABEL", "Convenience fee")

    # What the payment network charges us, passed through at cost. Keep these in
    # step with your Stripe pricing page — they are quoted to the client as
    # Stripe's fee, so they have to actually be Stripe's fee.
    STRIPE_CARD_PERCENT = float(os.environ.get("STRIPE_CARD_PERCENT", "2.9"))
    STRIPE_CARD_FIXED_CENTS = _int("STRIPE_CARD_FIXED_CENTS", 30)
    STRIPE_ACH_PERCENT = float(os.environ.get("STRIPE_ACH_PERCENT", "0.8"))
    STRIPE_ACH_CAP_CENTS = _int("STRIPE_ACH_CAP_CENTS", 500)
    PASS_THROUGH_PROCESSING = _bool("PASS_THROUGH_PROCESSING", True)

    # --- payments ---
    PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")  # mock | stripe
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    ENABLE_ACH = _bool("ENABLE_ACH", True)
    ENABLE_CARD = _bool("ENABLE_CARD", True)

    # --- session ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = _int("SESSION_DAYS", 14) * 86400
