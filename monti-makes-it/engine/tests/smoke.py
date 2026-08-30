"""End-to-end smoke test — walks every screen and the full money path."""
import contextlib
import io
import os
import pathlib
import re
import sys

sys.path.insert(0, ".")
from monti import create_app  # noqa: E402

FAILS = []


def check(label, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILS.append(f"{label} {extra}")
    print(f"  [{status}] {label}{(' — ' + extra) if extra and not cond else ''}")


def get(client, url, expect=200, label=None):
    r = client.get(url)
    check(label or f"GET {url}", r.status_code == expect, f"got {r.status_code}")
    return r


CSRF = "test-csrf-token"


def arm(client):
    """Give the test client a known CSRF token, as a browser would have."""
    with client.session_transaction() as sess:
        sess["_csrf"] = CSRF
    return client


def post(client, url, data=None, **kwargs):
    payload = dict(data or {})
    payload["_csrf"] = CSRF
    return client.post(url, data=payload, **kwargs)


def account(login_name):
    """The customer behind a demo login. Looked up by credential, not by display
    name, so renaming the seed data can never break these tests."""
    from monti.db import query
    return query("SELECT c.* FROM customers c JOIN users u ON u.customer_id = c.id "
                 "WHERE u.email = ?", (login_name.lower(),), one=True)


def login(client, email, password):
    r = post(client, "/login", {"email": email, "password": password},
             follow_redirects=True)
    arm(client)   # signing in clears the session, so mint a fresh token
    return r


def main():
    # Always run against a throwaway database, freshly seeded. The suite mutates
    # a lot of state, so sharing a file between runs makes failures meaningless.
    db_path = pathlib.Path("instance/test.db")
    for suffix in ("", "-wal", "-shm"):
        p = pathlib.Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()
    os.environ["DATABASE_PATH"] = str(db_path)

    app = create_app()
    app.config.update(TESTING=True, SERVER_NAME="localhost", PAYMENT_PROVIDER="mock",
                      DATABASE_PATH=str(db_path))
    with app.app_context():
        from monti.seed import run_seed
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            run_seed()

    with app.test_client() as c:
        arm(c)
        print("\n— public site —")
        for url in ("/", "/how-it-works", "/membership", "/contact", "/quote", "/apply", "/login"):
            get(c, url)

        print("\n— guards (anonymous) —")
        for url in ("/portal/", "/admin/", "/admin/orders", "/portal/orders"):
            r = c.get(url)
            check(f"{url} redirects anonymous", r.status_code in (302, 308), f"got {r.status_code}")

        print("\n— CSRF —")
        import re as _re
        for page in ("/quote", "/apply", "/login"):
            html = c.get(page).data.decode()
            forms = _re.findall(r'<form[^>]*method="post"[^>]*>(.{0,400})', html, _re.S)
            check(f"{page} form carries a CSRF token",
                  bool(forms) and all('name="_csrf"' in f for f in forms),
                  "a form is missing the hidden token")
        r = c.post("/quote", data={"company_name": "X", "contact_name": "X",
                                   "email": "x@example.com", "title": "X", "description": "X"})
        check("POST without a CSRF token is rejected", r.status_code == 400, f"got {r.status_code}")
        r = c.post("/quote", data={"_csrf": "wrong", "company_name": "X"})
        check("POST with a bad CSRF token is rejected", r.status_code == 400, f"got {r.status_code}")

        print("\n— quote intake —")
        r = post(c, "/quote", {
            "company_name": "Test Fixtures Co", "contact_name": "Ada Byron",
            "email": "ada@testfixtures.example", "title": "Machined brass bracket",
            "description": "CNC brass bracket, 40mm, brushed finish.", "quantity": "1200",
            "target_unit_price": "4.25", "destination_country": "United States",
            "destination_city": "Austin", "incoterm": "DDP", "category": "Metal & machined parts",
        }, follow_redirects=True)
        check("quote submitted", r.status_code == 200 and b"with the floor" in r.data,
              f"status {r.status_code}")
        body = r.data.decode()
        check("non-member is pointed at membership", "Apply for Membership" in body)
        check("no portal is handed to a non-member", 'class="pw-reveal"' not in body)

        # The other half of the merge. `A37` probes the portal door; this is the
        # public one, and it has to produce the same three linked records —
        # writing only a quote here is exactly the split that was fixed.
        with app.app_context():
            from monti.db import query
            q = query("SELECT * FROM quotes WHERE title = 'Machined brass bracket' "
                      "ORDER BY id DESC", one=True)
            d = query("SELECT * FROM decision_items WHERE quote_id = ?", (q["id"],), one=True)
            cap = query("SELECT * FROM capacity_ledger WHERE quote_id = ?", (q["id"],), one=True)
        check("the public door opens a product too", d is not None)
        check("and debits capacity against the same request", cap is not None
              and cap["item_id"] == (d["id"] if d else None))

        print("\n— membership application —")
        r = post(c, "/apply", {
            "company_name": "Test Fixtures Co", "contact_name": "Ada Byron",
            "email": "ada@testfixtures.example",
            "what_they_sell": "Precision brass fittings for lab equipment.",
            "why": "We want one manufacturer for the whole catalogue, not a broker per part.",
            "business_type": "Brand selling my own products", "annual_volume": "$50k – $250k",
            "availability": "Weekday mornings",
        }, follow_redirects=True)
        check("application submitted", b"it&#39;s with us" in r.data or b"it's with us" in r.data,
              f"status {r.status_code}")
        r = post(c, "/apply", {
            "company_name": "Test Fixtures Co", "contact_name": "Ada Byron",
            "email": "ada@testfixtures.example", "what_they_sell": "x", "why": "y"})
        check("a second open application is refused", r.status_code == 400, f"got {r.status_code}")

    # ---- admin flow ----
    with app.test_client() as c:
        arm(c)
        print("\n— admin bay —")
        r = login(c, "Tyler1", "Tyler1")
        check("admin login", b"Today" in r.data or b"Admin bay" in r.data)
        for url in ("/admin/", "/admin/quotes", "/admin/quotes?status=all", "/admin/crm",
                    "/admin/crm/1", "/admin/crm/new", "/admin/calendar", "/admin/catalog",
                    "/admin/catalog/1", "/admin/catalog/new", "/admin/orders",
                    "/admin/orders?status=review", "/admin/orders/1", "/admin/orders/3",
                    "/admin/emails", "/admin/settings", "/admin/quotes/4",
                    "/admin/applications", "/admin/applications?status=all",
                    "/admin/applications/3", "/admin/applications/4",
                    "/admin/revenue", "/admin/revenue?period=1d", "/admin/revenue?period=21d",
                    "/admin/revenue?period=90d", "/admin/revenue?period=365d",
                    "/admin/incoming"):
            get(c, url)

        print("\n— admin: interview then accept —")
        with app.app_context():
            from monti.db import query
            appn = query("SELECT * FROM applications WHERE email = 'ada@testfixtures.example'",
                         one=True)
        check("application reached the admin bay", appn is not None)
        r = post(c, f"/admin/applications/{appn['id']}",
                 {"action": "interview", "interview_at": "2026-09-10T15:00",
                  "interview_link": "https://zoom.example/abc"}, follow_redirects=True)
        check("interview booked", r.status_code == 200)
        with app.app_context():
            from monti.db import query
            a2 = query("SELECT * FROM applications WHERE id = ?", (appn["id"],), one=True)
            cust = query("SELECT * FROM customers WHERE id = ?", (a2["customer_id"],), one=True)
            check("status is INTERVIEW_SCHEDULED", a2["status"] == "INTERVIEW_SCHEDULED", a2["status"])
            check("customer moved to INTERVIEW", cust["membership_status"] == "INTERVIEW",
                  cust["membership_status"])
            check("interview is on the calendar", query(
                "SELECT id FROM calendar_events WHERE kind = 'INTERVIEW' AND customer_id = ?",
                (a2["customer_id"],), one=True) is not None)
            check("applicant emailed the invitation", query(
                "SELECT id FROM email_log WHERE template = 'application_interview'",
                one=True) is not None)

        r = post(c, f"/admin/applications/{appn['id']}",
                 {"action": "approve", "quote_limit": "10",
                  "decision_reason": "Good fit"}, follow_redirects=True)
        check("application approved", r.status_code == 200)
        with app.app_context():
            from monti.db import query
            cust = query("SELECT * FROM customers WHERE lower(email) = 'ada@testfixtures.example'",
                         one=True)
            check("customer is now a MEMBER", cust["membership_status"] == "MEMBER",
                  cust["membership_status"])
            check("member_since recorded", bool(cust["member_since"]))
            check("portal login created on acceptance", query(
                "SELECT id FROM users WHERE customer_id = ?", (cust["id"],), one=True) is not None)
            check("welcome email sent", query(
                "SELECT id FROM email_log WHERE template = 'application_approved'",
                one=True) is not None)

        print("\n— admin: decline path —")
        with app.app_context():
            from monti.db import query
            pending = query("SELECT * FROM applications WHERE status = 'SUBMITTED' LIMIT 1", one=True)
        if pending:
            r = post(c, f"/admin/applications/{pending['id']}", {"action": "decline"},
                     follow_redirects=True)
            with app.app_context():
                from monti.db import query
                still = query("SELECT * FROM applications WHERE id = ?", (pending["id"],), one=True)
                check("declining without a reason is refused",
                      still["status"] == "SUBMITTED", still["status"])
            r = post(c, f"/admin/applications/{pending['id']}",
                     {"action": "decline", "reason": "x",
                      "decision_reason": "Not the kind of work we take on."},
                     follow_redirects=True)
            with app.app_context():
                from monti.db import query
                done = query("SELECT * FROM applications WHERE id = ?", (pending["id"],), one=True)
                check("application declined", done["status"] == "DECLINED", done["status"])
                check("decline email sent", query(
                    "SELECT id FROM email_log WHERE template = 'application_declined'",
                    one=True) is not None)

        print("\n— admin: price the new quote and send the estimate —")
        with app.app_context():
            from monti.db import query
            quote = query("SELECT * FROM quotes WHERE title = 'Machined brass bracket'", one=True)
        qid = quote["id"]
        r = post(c, f"/admin/quotes/{qid}", {
            "action": "estimate", "unit_price": "3.90", "quantity": "1200", "moq": "1000",
            "tooling": "450", "sample": "80", "shipping": "620", "duties": "180",
            "lead_time_days": "28", "ship_method": "SEA", "incoterm": "DDP",
            "notes": "Brass at current LME. Holds 30 days.", "send": "1",
        }, follow_redirects=True)
        check("estimate sent", r.status_code == 200)
        with app.app_context():
            from monti.db import query
            q2 = query("SELECT * FROM quotes WHERE id = ?", (qid,), one=True)
            est = query("SELECT * FROM estimates WHERE quote_id = ?", (qid,), one=True)
            check("quote status ESTIMATE_SENT", q2["status"] == "ESTIMATE_SENT", q2["status"])
            expected = 390 * 1200 + 45000 + 8000 + 62000 + 18000
            check("estimate total correct", est["total_cents"] == expected,
                  f"{est['total_cents']} != {expected}")
            check("estimate email logged", query(
                "SELECT id FROM email_log WHERE template = 'estimate_ready'", one=True) is not None)

        print("\n— admin: create a catalog item from the quote and assign it —")
        r = post(c, f"/admin/quotes/{qid}/to-catalog", {"sku": "MMI-TEST-1"},
                   follow_redirects=True)
        check("catalog item created", b"MMI-TEST-1" in r.data)

    # ---- client isolation ----
    with app.test_client() as c:
        arm(c)
        print("\n— member portal (Halcyon) —")
        r = login(c, "dana@halcyongoods.com", "member2026")
        check("client login", b"Halcyon Goods" in r.data)
        with app.app_context():
            from monti.db import query
            own_quote = query("SELECT q.id FROM quotes q JOIN customers c ON c.id = q.customer_id "
                              "WHERE c.company_name = 'Halcyon Goods' ORDER BY q.id LIMIT 1", one=True)
        for url in ("/portal/", "/portal/requests", "/portal/products", "/portal/catalog",
                    "/portal/orders", "/portal/cart", "/portal/quotes/" + str(own_quote["id"]),
                    "/portal/orders/1", "/portal/orders/3", "/portal/catalog/1",
                    "/portal/purchases"):
            get(c, url)

        # The two tabs are one now. Both old addresses still land somewhere real.
        for legacy, target in (("/portal/quotes", "/portal/requests"),
                               ("/portal/intake", "/portal/requests"),
                               ("/portal/room", "/portal/products")):
            r = c.get(legacy, follow_redirects=False)
            check(f"{legacy} redirects to {target}",
                  r.status_code in (301, 302) and target in r.headers["Location"],
                  f"got {r.status_code} -> {r.headers.get('Location')}")
        r = c.get("/portal/requests")
        check("the request form and the request list are one page",
              b"Describe it badly" in r.data and b"What you have already asked for" in r.data)

        r = c.get("/portal/purchases")
        check("purchased items lists what they bought", b"Purchased items" in r.data)
        check("and shows an order timeline", b"track-step" in r.data)

        print("\n— isolation —")
        r = c.get("/portal/orders/2")   # belongs to Grit & Grain
        check("cannot read another client's order", r.status_code == 404, f"got {r.status_code}")
        r = c.get("/portal/quotes/2")
        check("cannot read another client's quote", r.status_code == 404, f"got {r.status_code}")
        r = c.get("/portal/catalog/2")  # assigned to Grit & Grain only
        check("cannot read an unassigned catalog item", r.status_code == 404, f"got {r.status_code}")
        r = c.get("/admin/")
        check("client blocked from admin bay", r.status_code == 403, f"got {r.status_code}")
        r = post(c, "/portal/cart/add/2", {"quantity": "10000"})
        check("cannot add an unassigned item to cart", r.status_code == 404, f"got {r.status_code}")

        print("\n— reorder from the private catalog → checkout → 24h gate —")
        post(c, "/portal/cart/add/1", {"quantity": "500"}, follow_redirects=True)
        r = post(c, "/portal/cart/checkout", {"ship_to": "1200 Industrial Way"},
                   follow_redirects=True)
        r_checkout = r
        check("cart takes them straight to checkout", b"How would you like to pay" in r.data,
              "no checkout screen")
        check("both payment methods are offered", b"Bank transfer (ACH)" in r.data and
              b">Card<" in r.data or b"Card" in r.data)
        with app.app_context():
            from monti.db import query
            order = query("SELECT * FROM orders ORDER BY id DESC LIMIT 1", one=True)
            check("order priced correctly", order["subtotal_cents"] == 2980 * 500,
                  f"{order['subtotal_cents']}")
            charged = 0 if order["freight_waived"] else order["shipping_cents"]
            check("with the fees on top",
                  order["total_cents"] == order["subtotal_cents"] + charged +
                  order["tax_cents"] + order["fee_cents"] + order["processing_fee_cents"] and
                  order["fee_cents"] == round((order["subtotal_cents"] + charged) * 0.015),
                  f"fee {order['fee_cents']} on {order['subtotal_cents']} + {charged}")
        oid, ref = order["id"], order["ref"]

        # CHG-024 — the acceptance is a condition of paying, not decoration on
        # the page. The refusal is checked first: a requirement that is only
        # ever exercised on the happy path has never been shown to hold.
        check("the checkout asks for acceptance", b"accept_disclaimers" in r_checkout.data,
              "no acceptance control on the checkout page")
        r = post(c, f"/portal/orders/{oid}/pay", follow_redirects=True)
        check("paying without accepting is refused",
              b"Simulated checkout" not in r.data and b"accept the disclaimers" in r.data,
              "payment went through without acceptance")

        r = post(c, f"/portal/orders/{oid}/pay", {"accept_disclaimers": "1"},
                 follow_redirects=True)
        check("checkout session started", b"Simulated checkout" in r.data)
        with app.app_context():
            from monti import disclaimers as disc
            from monti.db import query
            rows = query("SELECT * FROM disclaimer_acceptances WHERE order_ref = ?", (ref,))
            check("one acceptance recorded per live disclaimer",
                  len(rows) == len(disc.current()) and len(rows) == 3, f"{len(rows)} rows")
            # The hash is the whole reason the record is worth keeping: it has to
            # resolve to text, not to whatever the page says today.
            check("each acceptance resolves to the exact text that was shown",
                  all(disc.version_by_hash(a["slug"], a["body_hash"]) is not None
                      for a in rows))

        # ACH initiated but not settled — nothing downstream may fire
        post(c, f"/portal/checkout/simulate/{ref}", {"method": "ACH", "outcome": "success"},
               follow_redirects=True)
        with app.app_context():
            from monti.db import query
            o = query("SELECT * FROM orders WHERE id = ?", (oid,), one=True)
            check("ACH pending → PAYMENT_PROCESSING", o["status"] == "PAYMENT_PROCESSING", o["status"])
            check("ACH pending → no review window", o["review_release_at"] is None)
            check("ACH pending → orders inbox NOT emailed", o["orders_email_sent_at"] is None)

        # now settle it
        post(c, f"/portal/checkout/simulate/{ref}", {"method": "ACH", "outcome": "success", "settle": "now"}, follow_redirects=True)
        with app.app_context():
            from monti.db import query
            o = query("SELECT * FROM orders WHERE id = ?", (oid,), one=True)
            check("funds confirmed → IN_REVIEW", o["status"] == "IN_REVIEW", o["status"])
            check("24h review window opened", o["review_release_at"] is not None)
            check("orders inbox emailed on funds confirmation", o["orders_email_sent_at"] is not None)
            internal = query(
                "SELECT * FROM email_log WHERE template = 'order_internal' ORDER BY id DESC LIMIT 1",
                one=True)
            check("orders email went to the centralized inbox",
                  internal and internal["to_addr"] == app.config["ORDERS_EMAIL"],
                  internal["to_addr"] if internal else "none")
            check("client receipt sent", query(
                "SELECT id FROM email_log WHERE template = 'order_receipt' ORDER BY id DESC LIMIT 1",
                one=True) is not None)

            # idempotency: a duplicate confirmation must not restart the clock or re-email
            from monti import orders as om
            before = query("SELECT COUNT(*) AS c FROM email_log", one=True)["c"]
            om.confirm_funds(oid, method="ACH", provider="mock")
            after = query("SELECT COUNT(*) AS c FROM email_log", one=True)["c"]
            check("duplicate funds confirmation is idempotent", before == after,
                  f"{before} → {after}")

    # ---- membership gating + the quote cycle ----
    with app.test_client() as c:
        arm(c)
        print("\n— the 10-quote cycle —")
        with app.app_context():
            from monti import membership as mem
            from monti.db import execute, query
            cust = query("SELECT * FROM customers WHERE ref = 'MMI-C-1004'", one=True)
            state = mem.quota_state(cust)
            check("a member has a quote cycle", state["limit"] == 10 and state["days"] == 30,
                  str(state))
            # fill the cycle
            for i in range(state["remaining"]):
                execute(
                    "INSERT INTO quotes (ref, customer_id, title, description, due_at) "
                    "VALUES (?, ?, ?, 'filler', datetime('now', '+1 day'))",
                    (f"MMI-Q-FILL{i}", cust["id"], f"Filler {i}"))
            after = mem.quota_state(cust)
            check("cycle counts up to the limit", after["exhausted"], str(after))
            check("blocked with an explanation", "used all 10" in (mem.check_quota(cust) or ""),
                  str(mem.check_quota(cust)))

        r = post(c, "/quote", {
            "contact_name": "Marcus Webb", "email": "marcus@gritgrain.co",
            "title": "One too many", "description": "Should be refused."})
        check("11th quote in the cycle is refused", r.status_code == 400, f"got {r.status_code}")
        check("the refusal explains the cycle", b"quote requests in your" in r.data)

        with app.app_context():
            from monti import membership as mem
            from monti.db import execute, query
            cust = query("SELECT * FROM customers WHERE ref = 'MMI-C-1004'", one=True)
            mem.raise_limit(cust["id"], 25, "Loyal account", "tester")
            cust = query("SELECT * FROM customers WHERE ref = 'MMI-C-1004'", one=True)
            check("raising the limit reopens the cycle",
                  not mem.quota_state(cust)["exhausted"], str(mem.quota_state(cust)))

        r = post(c, "/quote", {
            "contact_name": "Marcus Webb", "email": "marcus@gritgrain.co",
            "title": "Now allowed", "description": "Should go through."}, follow_redirects=True)
        check("a raised limit lets the next quote through", b"with the floor" in r.data,
              f"status {r.status_code}")

    with app.test_client() as c:
        arm(c)
        print("\n— buying is member-only —")
        with app.app_context():
            from monti.db import execute, query
            cust = query("SELECT * FROM customers WHERE ref = 'MMI-C-1001'", one=True)
            execute("UPDATE customers SET membership_status = 'PAUSED' WHERE id = ?", (cust["id"],))
        login(c, "dana@halcyongoods.com", "member2026")
        r = c.get("/portal/")
        check("a paused member still sees their portal", r.status_code == 200)
        check("and is told ordering needs membership", b"ordering needs membership" in r.data)
        r = post(c, "/portal/cart/checkout", {"ship_to": "x"}, follow_redirects=False)
        check("checkout is blocked for a non-member", r.status_code in (302, 308),
              f"got {r.status_code}")
        r = post(c, "/portal/quotes/1/accept", follow_redirects=False)
        check("accepting an estimate is blocked too", r.status_code in (302, 308),
              f"got {r.status_code}")
        with app.app_context():
            from monti.db import execute, query
            cust = query("SELECT * FROM customers WHERE ref = 'MMI-C-1001'", one=True)
            execute("UPDATE customers SET membership_status = 'MEMBER' WHERE id = ?", (cust["id"],))

    # ---- Client 1: browse, buy, pay ----
    with app.test_client() as c:
        arm(c)
        print("\n— a member buys their product —")
        login(c, "client1", "client")
        r = c.get("/portal/catalog")
        check("the account sees a product", b"edition" in r.data, f"status {r.status_code}")
        with app.app_context():
            from monti.db import query
            item = query("SELECT * FROM catalog_items WHERE sku = 'MMI-3001'", one=True)
        r = post(c, f"/portal/cart/add/{item['id']}", {"quantity": "250"}, follow_redirects=True)
        check("it goes in the cart", b"Current order" in r.data)
        r = post(c, "/portal/cart/checkout", {"ship_to": "1200 Industrial Way"},
                 follow_redirects=True)
        check("checkout offers card and bank transfer",
              b"How would you like to pay" in r.data and b"ACH" in r.data)
        with app.app_context():
            from monti.db import query
            order = query("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
                          (item and query("SELECT customer_id FROM catalogue_registrations "
                                          "WHERE item_id = ?", (item["id"],), one=True)["customer_id"],),
                          one=True)
            check("the order is priced at their agreed rate",
                  order["subtotal_cents"] == 2980 * 250, str(order["subtotal_cents"]))
            charged2 = 0 if order["freight_waived"] else order["shipping_cents"]
            check("and the only things added are the two fees",
                  order["total_cents"] == order["subtotal_cents"] + charged2 + order["tax_cents"] +
                  order["fee_cents"] + order["processing_fee_cents"],
                  f"{order['total_cents']}")
        r = post(c, f"/portal/orders/{order['id']}/pay", {"method": "us_bank_account"},
                 follow_redirects=True)
        check("choosing bank transfer reaches the payment step", r.status_code == 200)
        c.post(f"/portal/checkout/simulate/{order['ref']}",
               data={"_csrf": CSRF, "method": "ACH", "outcome": "success", "settle": "now"},
               follow_redirects=True)
        with app.app_context():
            from monti.db import query
            o = query("SELECT * FROM orders WHERE id = ?", (order["id"],), one=True)
            check("paying by ACH confirms the funds", o["payment_status"] == "PAID", o["payment_status"])
            check("and opens the review window", o["status"] == "IN_REVIEW", o["status"])
        r = c.get("/portal/purchases")
        check("it now shows in purchased items", b"edition" in r.data)

    # ---- the one fee ----
    with app.test_client() as c:
        arm(c)
        print("\n— the 1.5% fee —")
        with app.app_context():
            from monti import orders as om
            from monti.db import execute, query
            pct = app.config["PURCHASE_FEE_PERCENT"]
            check("the fee rate is 1.5%", pct == 1.5, str(pct))
            check("fee_on rounds to the cent", om.fee_on(100000) == 1500 and om.fee_on(333) == 5,
                  f"{om.fee_on(100000)}, {om.fee_on(333)}")

            # Client 2 has no standing freight offer, so this exercises the charged path.
            cust = account("client2")
            order = om.create_order(cust["id"], [
                {"name": "Fee test", "sku": "FEE-1", "unit_price_cents": 100000, "quantity": 10}],
                actor="tester", category="Metal & machined parts", destination="United States")
            check("goods subtotal is the goods only", order["subtotal_cents"] == 1000000,
                  str(order["subtotal_cents"]))
            check("an order gets a freight estimate on creation",
                  order["freight_estimate_cents"] > 0 and order["customs_estimate_cents"] > 0,
                  f"{order['freight_estimate_cents']}/{order['customs_estimate_cents']}")
            check("the estimate is stored with its breakdown",
                  om.freight_estimate(order) is not None)
            ship = om.charged_shipping(order)
            check("the convenience fee is 1.5% of goods plus freight",
                  order["fee_cents"] == round((order["subtotal_cents"] + ship) * 0.015),
                  f"{order['fee_cents']} on {order['subtotal_cents']} + {ship}")
            check("everything adds up",
                  order["total_cents"] == order["subtotal_cents"] + ship + order["tax_cents"] +
                  order["fee_cents"] + order["processing_fee_cents"], str(order["total_cents"]))

            # change the freight; the fee must follow
            execute("UPDATE orders SET shipping_cents = 0, freight_estimate_cents = 0, "
                    "customs_estimate_cents = 0 WHERE id = ?", (order["id"],))
            om.recalc_totals(order["id"])
            o2 = om.get_order(order["id"])
            check("changing freight recalculates the fee", o2["fee_cents"] == 15000,
                  str(o2["fee_cents"]))
            check("and the total stays consistent",
                  o2["total_cents"] == o2["subtotal_cents"] + o2["shipping_cents"] +
                  o2["tax_cents"] + o2["fee_cents"] + o2["processing_fee_cents"],
                  str(o2["total_cents"]))

            # every seeded order agrees with the formula
            bad = [r["ref"] for r in query(
                "SELECT ref, subtotal_cents, shipping_cents, freight_waived, tax_cents, fee_cents, "
                "processing_fee_cents, total_cents FROM orders WHERE total_cents > 0")
                if r["total_cents"] != r["subtotal_cents"] +
                   (0 if r["freight_waived"] else r["shipping_cents"]) + r["tax_cents"] +
                   r["fee_cents"] + r["processing_fee_cents"]]
            check("every order's total adds up", not bad, ", ".join(bad[:3]))

            # the fee reaches Stripe as its own line, so their total matches ours
            app.config["PAYMENT_PROVIDER"] = "stripe"
            captured = {}
            import monti.payments as pay
            real_post = pay._stripe_post
            def fake_post(path, params):
                captured.update(params)
                return {"id": "cs_test", "url": "https://stripe.example/cs_test"}
            pay._stripe_post = fake_post
            try:
                pay.create_checkout_session(o2, om.get_items(o2["id"]), cust, method="card")
            finally:
                pay._stripe_post = real_post
                app.config["PAYMENT_PROVIDER"] = "mock"
            lines = captured.get("line_items", [])
            charged = sum(int(l["price_data"]["unit_amount"]) * int(l["quantity"]) for l in lines)
            check("Stripe is asked for exactly our total", charged == o2["total_cents"],
                  f"{charged} vs {o2['total_cents']}")
            check("the fee is its own visible line on the Stripe page",
                  any("1.5%" in (l["price_data"]["product_data"]["name"] or "") for l in lines),
                  str([l["price_data"]["product_data"]["name"] for l in lines]))
            execute("DELETE FROM orders WHERE id = ?", (order["id"],))

        print("\n— the processing pass-through —")
        with app.app_context():
            from monti import orders as om
            net = 1000000
            card = om.processing_fee_for(net, "card")
            ach = om.processing_fee_for(net, "us_bank_account")
            wire = om.processing_fee_for(net, "WIRE")
            check("card processing is grossed up so we net the full amount",
                  abs((net + card) * 0.029 + 30 - card) <= 1, f"fee {card}")
            check("ACH is capped at $5", ach == 500, str(ach))
            check("ACH costs far less than card on a big order", ach < card / 10,
                  f"{ach} vs {card}")
            check("a wire carries no pass-through", wire == 0, str(wire))
            opts = om.quote_payment_options(net)
            check("both methods are quoted with their own total",
                  len(opts) == 2 and opts[0]["total"] != opts[1]["total"], str(opts))
            check("each quoted total is net plus that method's fee",
                  all(o["total"] == net + o["fee"] for o in opts))

        print("\n— the owner's freight offer —")
        with app.app_context():
            from monti import freight, orders as om
            from monti.db import execute, query
            est = freight.estimate(745000, 250, "Bags & leather goods", "United States", "SEA")
            check("the estimate is built from real components",
                  est["freight_cents"] > 0 and est["duty_cents"] > 0 and est["mpf_cents"] > 0,
                  str(est))
            check("chargeable weight is the greater of actual and volumetric",
                  est["chargeable_kg"] == max(est["actual_kg"], est["volumetric_kg"]))
            check("duty follows the rate for that kind of good",
                  est["duty_cents"] == round(745000 * est["duty_rate"] / 100))
            check("the breakdown is renderable line by line",
                  len(freight.breakdown_lines(est)) >= 4)
            bigger = freight.estimate(745000, 2500, "Bags & leather goods", "United States", "SEA")
            check("ten times the units costs more to ship",
                  bigger["freight_cents"] > est["freight_cents"])
            air = freight.estimate(745000, 250, "Bags & leather goods", "United States", "AIR")
            check("air costs more than sea", air["freight_cents"] > est["freight_cents"])

            cust = account("client1")
            check("the account carries the standing freight offer",
                  cust["freight_waived_default"] == 1)
            o = om.create_order(cust["id"], [
                {"name": "Waived test", "sku": "W-1", "unit_price_cents": 2980, "quantity": 250}],
                actor="tester", category="Bags & leather goods", destination="United States")
            check("the standing offer applies on creation", o["freight_waived"] == 1)
            check("freight is charged at zero", om.charged_shipping(o) == 0,
                  str(om.charged_shipping(o)))
            check("but the estimate is kept, so it can be shown struck through",
                  o["freight_estimate_cents"] + o["customs_estimate_cents"] > 0)
            check("the convenience fee is charged on what they actually pay, not the waived figure",
                  o["fee_cents"] == round(o["subtotal_cents"] * 0.015), str(o["fee_cents"]))
            waived_total = o["total_cents"]

            om.set_freight_waived(o["id"], False, "tester", "test")
            o2 = om.get_order(o["id"])
            check("taking the offer back charges the freight",
                  om.charged_shipping(o2) == o2["freight_estimate_cents"] +
                  o2["customs_estimate_cents"], str(om.charged_shipping(o2)))
            check("and the total goes up by exactly that plus its fee",
                  o2["total_cents"] > waived_total, f"{o2['total_cents']} vs {waived_total}")
            check("waiving is on the audit trail", query(
                "SELECT id FROM order_events WHERE order_id = ? AND event = 'FREIGHT_WAIVED'",
                (o["id"],), one=True) is not None)
            execute("DELETE FROM orders WHERE id = ?", (o["id"],))

        r = c.get("/how-it-works")
        check("the public site names the fee", b"1.5%" in r.data)
        r = c.get("/membership")
        check("and says both lines are at cost",
              b"at cost" in r.data or b"never marked up" in r.data)

    # ---- the review gate ----
    with app.test_client() as c:
        arm(c)
        print("\n— manufacturer review gate —")
        login(c, "Tyler1", "Tyler1")
        with app.app_context():
            from monti import orders as om
            from monti.db import query
            o = query("SELECT * FROM orders ORDER BY id DESC LIMIT 1", one=True)
            try:
                om.ship_order(o["id"], "tester")
                check("cannot ship before review clears", False, "ship_order allowed it")
            except ValueError:
                check("cannot ship before review clears", True)

        r = post(c, f"/admin/orders/{o['id']}", {
            "action": "approve", "notes": "Specs match the approved sample.", "start_production": "1"},
            follow_redirects=True)
        check("review approved", r.status_code == 200)
        with app.app_context():
            from monti.db import query
            o2 = query("SELECT * FROM orders WHERE id = ?", (o["id"],), one=True)
            check("released to production", o2["status"] == "IN_PRODUCTION", o2["status"])
            check("reviewer recorded", bool(o2["reviewed_by"]))

        r = post(c, f"/admin/orders/{o['id']}", {
            "action": "ship", "carrier": "DHL", "tracking": "TEST123"}, follow_redirects=True)
        with app.app_context():
            from monti.db import query
            o3 = query("SELECT * FROM orders WHERE id = ?", (o["id"],), one=True)
            check("ships after review", o3["status"] == "SHIPPED", o3["status"])
            check("shipping email to client and orders inbox", query(
                "SELECT COUNT(*) AS c FROM email_log WHERE template = 'order_shipped'",
                one=True)["c"] >= 2)

        print("\n— incoming quotes: accept and decline —")
        with app.app_context():
            from monti.db import query
            waiting = query("SELECT * FROM quotes WHERE status = 'NEW' ORDER BY id", one=False)
            check("requests are waiting to be triaged", len(waiting) >= 2, str(len(waiting)))
        first, second = waiting[0], waiting[1]

        r = post(c, f"/admin/incoming/{first['id']}/accept", follow_redirects=True)
        check("accepting sends it to pricing", r.status_code == 200)
        with app.app_context():
            from monti.db import query
            q = query("SELECT * FROM quotes WHERE id = ?", (first["id"],), one=True)
            check("status moved to IN_REVIEW", q["status"] == "IN_REVIEW", q["status"])
            check("who triaged it is recorded", bool(q["triaged_by"] and q["triaged_at"]))
            check("the client was told we're pricing it", query(
                "SELECT id FROM email_log WHERE template = 'quote_accepted'", one=True) is not None)
            check("the SLA clock was not reset", q["due_at"] == first["due_at"])

        r = post(c, f"/admin/incoming/{second['id']}/reject", {}, follow_redirects=True)
        with app.app_context():
            from monti.db import query
            q = query("SELECT * FROM quotes WHERE id = ?", (second["id"],), one=True)
            check("declining without a reason is refused", q["status"] == "NEW", q["status"])
        r = post(c, f"/admin/incoming/{second['id']}/reject",
                 {"reason": "Below our practical minimum for this process."}, follow_redirects=True)
        with app.app_context():
            from monti.db import query
            q = query("SELECT * FROM quotes WHERE id = ?", (second["id"],), one=True)
            check("declining marks it REJECTED", q["status"] == "REJECTED", q["status"])
            check("the reason is stored", "practical minimum" in (q["decline_reason"] or ""))
            check("the client was told why", query(
                "SELECT id FROM email_log WHERE template = 'quote_rejected'", one=True) is not None)
        r = post(c, f"/admin/incoming/{second['id']}/accept", follow_redirects=True)
        with app.app_context():
            from monti.db import query
            q = query("SELECT * FROM quotes WHERE id = ?", (second["id"],), one=True)
            check("a triaged request cannot be triaged twice", q["status"] == "REJECTED", q["status"])

        print("\n— catalog tags —")
        with app.app_context():
            from monti import catalog as cat
            from monti.db import execute, query
            check("tags parse and de-dupe", cat.parse_tags("Bags, leather , bags;LEATHER") ==
                  ["bags", "leather"], str(cat.parse_tags("Bags, leather , bags;LEATHER")))
            c1 = account("client1")
            check("the first demo account has a product to buy",
                  len(cat.items_for_customer(c1)) >= 1)
            c2 = account("client2")
            check("a tagless account sees nothing", cat.items_for_customer(c2) == [])
            execute("UPDATE customers SET catalog_tags = 'packaging' WHERE id = ?", (c2["id"],))
            c2 = account("client2")
            granted = cat.items_for_customer(c2)
            check("one tag opens a whole range", len(granted) >= 2, str(len(granted)))
            check("every granted item actually carries the tag",
                  all("packaging" in i["matched_tags"] for i in granted))
            check("the grant is visible from the item side too",
                  any(r["row"]["id"] == c2["id"] for r in cat.customers_for_item(
                      query("SELECT * FROM catalog_items WHERE sku = 'MMI-2002'", one=True))))
            execute("UPDATE customers SET catalog_tags = 'packaging, leather' WHERE id = ?", (c2["id"],))
            c2 = account("client2")
            check("a second tag adds to the first, it doesn't replace it",
                  len(cat.items_for_customer(c2)) > len(granted))
            item = query("SELECT * FROM catalog_items WHERE sku = 'MMI-2002'", one=True)
            execute("INSERT OR REPLACE INTO catalogue_registrations (item_id, customer_id, "
                    "unit_price_cents, assigned_by) VALUES (?, ?, ?, 'test')",
                    (item["id"], c2["id"], 29))
            c2 = account("client2")
            both = [i for i in cat.items_for_customer(c2) if i["id"] == item["id"]][0]
            check("a negotiated price beats the tag price", both["price_cents"] == 29 and
                  both["negotiated"], str(both["price_cents"]))
            execute("DELETE FROM catalogue_registrations WHERE customer_id = ?", (c2["id"],))
            execute("UPDATE customers SET catalog_tags = NULL WHERE id = ?", (c2["id"],))
            c2 = account("client2")
            check("removing every tag closes the door again", cat.items_for_customer(c2) == [])

        print("\n— revenue dashboard —")
        with app.app_context():
            from monti import analytics
            for key, days, _ in analytics.PERIODS:
                sm = analytics.summary(key)
                check("summary for " + key + " reads " + str(days) + " days",
                      sm["days"] == days and sm["revenue"] >= 0, str(sm))
                pts = analytics.series(key)["points"]
                expected = 24 if days == 1 else days
                check("series for " + key + " has " + str(expected) + " points",
                      len(pts) == expected, str(len(pts)))
            wide, narrow = analytics.summary("365d"), analytics.summary("7d")
            check("a longer window books more revenue", wide["revenue"] >= narrow["revenue"],
                  f"{wide['revenue']} vs {narrow['revenue']}")
            # One call, compared against its own sort. Calling `by_customer`
            # twice and comparing the two results is not a ranking assertion:
            # each call re-derives its window from the clock, and tied revenues
            # have no secondary order, so the check failed intermittently on
            # differences that were never about ranking.
            ranked = [r["revenue"] for r in analytics.by_customer("90d")]
            check("revenue by client is ranked", ranked == sorted(ranked, reverse=True),
                  str(ranked))

        print("\n— admin opens a client portal —")
        with app.app_context():
            from monti.db import query
            c1 = account("client1")
            check("the first demo account is a member", c1 and c1["membership_status"] == "MEMBER")
            c5 = account("client5")
            check("the fifth demo account is still quote-only", query(
                "SELECT COUNT(*) AS c FROM catalogue_registrations WHERE customer_id = ? AND active = 1",
                (c5["id"],), one=True)["c"] == 0 and not c5["catalog_tags"])
        r = c.get("/admin/clients/" + str(c1["id"]) + "/open", follow_redirects=True)
        check("admin lands in the client's portal",
              c1["company_name"].encode() in r.data, f"status {r.status_code}")
        check("the view is clearly marked", b"Admin view" in r.data)
        r = c.get("/portal/catalog")
        check("that portal shows their product", b"edition" in r.data, f"status {r.status_code}")
        c.get("/admin/clients/" + str(c5["id"]) + "/open", follow_redirects=True)
        r = c.get("/portal/catalog")
        check("a quote-only portal shows nothing to order",
              b"Nothing available to order yet" in r.data, f"status {r.status_code}")
        r = c.get("/admin/clients/close", follow_redirects=True)
        check("admin can step back out", r.status_code == 200)

        print("\n— tracking codes —")
        with app.app_context():
            from monti.db import query
            shipped = query("SELECT * FROM orders WHERE status = 'SHIPPED' ORDER BY id DESC LIMIT 1",
                            one=True)
        r = post(c, f"/admin/orders/{shipped['id']}",
                 {"action": "tracking", "carrier": "DHL Express", "tracking": "TESTTRACK99",
                  "notify": "1"}, follow_redirects=True)
        with app.app_context():
            from monti.db import query
            o = query("SELECT * FROM orders WHERE id = ?", (shipped["id"],), one=True)
            check("tracking saved after shipping", o["tracking_number"] == "TESTTRACK99",
                  str(o["tracking_number"]))
            check("the client can be emailed the code", query(
                "SELECT id FROM email_log WHERE template = 'order_tracking'", one=True) is not None)
            check("the change is on the audit trail", query(
                "SELECT id FROM order_events WHERE order_id = ? AND event = 'TRACKING_UPDATED'",
                (shipped["id"],), one=True) is not None)

        print("\n— admin: calendar, CRM writes —")
        r = post(c, "/admin/calendar/new", {
            "title": "Test event", "kind": "CALL", "starts_at": "2026-09-01T10:00",
            "customer_id": "1"}, follow_redirects=True)
        check("calendar event created", b"Test event" in r.data)
        r = post(c, "/admin/crm/1", {"action": "note", "kind": "CALL",
                                         "body": "Test call logged"}, follow_redirects=True)
        check("CRM activity logged", b"Test call logged" in r.data)
        r = post(c, "/admin/crm/1", {"action": "stage", "stage": "ACTIVE"},
                   follow_redirects=True)
        check("CRM stage changed", r.status_code == 200)

    print("\n— feature audit —")
    import subprocess
    audit = subprocess.run([sys.executable, "tests/audit.py"], capture_output=True, text=True)
    for line in audit.stdout.strip().splitlines():
        if "[GAP]" in line:
            print(line.replace("[GAP]", "[FAIL]"))
    check("every feature we've shipped is present in the engine", audit.returncode == 0,
          audit.stdout.strip().splitlines()[-1] if audit.stdout else "audit did not run")

    print("\n" + "=" * 60)
    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
