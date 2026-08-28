"""Does the engine actually carry everything we've built and shown?

Walks the running app's route table and module surface, so this is what the code
says, not what the notes say.
"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("SECRET_KEY", "audit")
from monti import create_app

app = create_app()
rules = {str(r) for r in app.url_map.iter_rules()}
endpoints = {r.endpoint for r in app.url_map.iter_rules()}

def has_route(path):
    return any(path == r or path in r for r in rules)

import monti.orders as orders, monti.catalog as catalog, monti.freight as freight
import monti.analytics as analytics, monti.membership as membership, monti.payments as payments

CHECKS = [
    # public
    ("Landing page with the two doors",        has_route("/") and has_route("/quote") and has_route("/apply")),
    ("How it works / membership pages",        has_route("/how-it-works") and has_route("/membership")),
    ("Quote intake with 24h SLA",              "QUOTE_SLA_HOURS" in app.config),
    ("Membership application + interview",     hasattr(membership, "schedule_interview")
                                               and hasattr(membership, "approve_application")
                                               and hasattr(membership, "decline_application")),
    ("10-quote rolling cycle, per account",    hasattr(membership, "quota_state")
                                               and hasattr(membership, "check_quota")
                                               and hasattr(membership, "raise_limit")),
    # admin
    ("Admin login + admin-only guard",         "admin.dashboard" in endpoints),
    ("Revenue, all seven periods",             len(analytics.PERIODS) == 7
                                               and has_route("/admin/revenue")),
    ("Revenue by client",                      hasattr(analytics, "by_customer")),
    ("Incoming quotes triage",                 has_route("/admin/incoming")
                                               and "admin.triage" in endpoints),
    ("CRM list + record",                      "admin.crm" in endpoints and "admin.crm_detail" in endpoints),
    ("Items catalog + per-item detail",        "admin.catalog" in endpoints and "admin.catalog_detail" in endpoints),
    ("Calendar",                               "admin.calendar_view" in endpoints),
    ("Open any client's portal",               "admin.open_client" in endpoints and "admin.close_client" in endpoints),
    ("Email log + settings",                   "admin.emails" in endpoints and "admin.settings" in endpoints),
    ("Applications queue",                     "admin.applications" in endpoints
                                               and "admin.application_detail" in endpoints),
    ("Tracking code, editable after shipping", "TRACKING_UPDATED" in open("monti/blueprints/admin.py").read()),
    ("Waive / reinstate freight",              hasattr(orders, "set_freight_waived")),
    # member portal
    ("Member portal, sealed per customer",     "portal.dashboard" in endpoints),
    ("Purchased items with timeline",          "portal.purchases" in endpoints),
    ("Checkout screen with method choice",     "portal.checkout" in endpoints),
    ("Catalog by tag or assignment",           hasattr(catalog, "items_for_customer")
                                               and hasattr(catalog, "customers_for_item")
                                               and hasattr(catalog, "all_tags")),
    # money
    ("1.5% convenience fee",                   app.config["PURCHASE_FEE_PERCENT"] == 1.5
                                               and hasattr(orders, "fee_on")),
    ("Stripe fee passed through, grossed up",  hasattr(orders, "processing_fee_for")
                                               and app.config["STRIPE_CARD_PERCENT"] == 2.9),
    ("Both methods priced side by side",       hasattr(orders, "quote_payment_options")),
    ("Freight + customs estimator",            hasattr(freight, "estimate")
                                               and hasattr(freight, "breakdown_lines")),
    ("Estimate stored per order, auditable",   hasattr(orders, "attach_freight_estimate")
                                               and hasattr(orders, "freight_estimate")),
    ("24h manufacturer review gate",           hasattr(orders, "review_state")
                                               and hasattr(orders, "approve_review")),
    ("Centralised orders email on funds",      hasattr(orders, "confirm_funds")),
    ("Stripe card + ACH, webhook verified",    hasattr(payments, "verify_webhook")
                                               and "us_bank_account" in open("monti/payments.py").read()),
    ("CSRF on every state change",             "check_csrf" in open("monti/auth.py").read()),
]

width = max(len(name) for name, _ in CHECKS)
missing = 0
for name, ok in CHECKS:
    if not ok:
        missing += 1
    print(f"  [{'OK ' if ok else 'GAP'}] {name.ljust(width)}")
print()
print(f"{len(CHECKS) - missing}/{len(CHECKS)} present" + ("" if not missing else f" — {missing} GAP(S)"))
sys.exit(1 if missing else 0)
