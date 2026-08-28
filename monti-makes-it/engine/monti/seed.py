"""Demo data — a believable slice of the business so every screen has something in it.

Every row this module writes is fixture data and is stamped as such before the
function returns. §0.3.5 requires that zero seeded rows survive to launch, and
the only way to prove that is to know which rows are seeded — recognising a name
afterwards is not proof, it is a reviewer's memory. `flask purge-fixtures`
sweeps on the stamp, and A14 asserts the sweep was total.

This command refuses to run against a database that already carries real
customers, because "load the demo data" and "you have live clients" is a
combination that ends with Halcyon Goods in a production order log.
"""
from datetime import timedelta

from flask import current_app

from .auth import create_user
from .db import FIXTURE_TABLES, execute, init_db, next_ref, query
from .utils import now_str, plus_hours, utcnow

ADMIN_EMAIL = "Tyler1"
ADMIN_PASSWORD = "Tyler1"
CLIENT_PASSWORD = "client"


def _ts(days=0, hours=0):
    return (utcnow() + timedelta(days=days, hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def _mark_fixtures():
    """Stamp everything this module wrote.

    Applied wholesale at the end rather than column by column at each INSERT:
    the demo seed's output is fixture data in its entirety, and a per-statement
    flag is one forgotten INSERT away from a row that survives the purge.
    """
    for table in FIXTURE_TABLES:
        execute(f"UPDATE {table} SET is_fixture = 1")


def run_seed():
    init_db()
    if query("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,), one=True):
        print("Already seeded — skipping. Delete the database file to reseed.")
        return

    real = query("SELECT COUNT(*) AS c FROM customers WHERE is_fixture = 0", one=True)
    if real["c"]:
        raise SystemExit(
            f"Refusing to seed: this database already has {real['c']} real customer(s). "
            "Demo data and live clients must not share a database.")

    create_user(ADMIN_EMAIL, ADMIN_PASSWORD, name="Tyler Monti", role="ADMIN")

    customers = [
        # ref, company, contact, email, phone, country, city, stage, source, owner, tags,
        # membership_status, quote_limit
        ("MMI-C-1001", "Halcyon Goods", "Dana Reyes", "dana@halcyongoods.com", "+1 503 555 0142",
         "United States", "Portland", "ACTIVE", "REFERRAL", "Tyler Monti", "apparel, repeat",
         "MEMBER", 16),
        ("MMI-C-1002", "Northfield Outfitters", "Sam Iyer", "sam@northfieldout.com", "+1 612 555 0119",
         "United States", "Minneapolis", "QUOTING", "WEBSITE", "Tyler Monti", "bags, seasonal",
         "APPLIED", 10),
        ("MMI-C-1003", "Verano Skincare", "Lucia Ortiz", "lucia@veranoskin.com", "+1 305 555 0177",
         "United States", "Miami", "NEGOTIATING", "WEBSITE", "Tyler Monti", "packaging, beauty",
         "INTERVIEW", 10),
        ("MMI-C-1004", "Grit & Grain Coffee", "Marcus Webb", "marcus@gritgrain.co", "+1 206 555 0163",
         "United States", "Seattle", "ACTIVE", "REFERRAL", "Tyler Monti", "packaging, repeat",
         "MEMBER", 10),
        ("MMI-C-1005", "Solace Home", "Priya Nair", "priya@solacehome.uk", "+44 20 7946 0102",
         "United Kingdom", "London", "LEAD", "OUTBOUND", "Tyler Monti", "furniture",
         "PROSPECT", 10),
    ]
    for row in customers:
        execute(
            "INSERT INTO customers (ref, company_name, contact_name, email, phone, country, city, "
            "stage, source, owner, tags, membership_status, quote_limit, member_since, "
            "membership_note, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row + (_ts(days=-120) if row[11] == "MEMBER" else None,
                   "Raised to 16 — develops a full line each season." if row[12] == 16 else None,
                   "1200 Industrial Way\nSuite 400"))

    applications = [
        # ref, customer, company, contact, email, what they sell, why, status, extras
        ("MMI-A-1001", 1, "Halcyon Goods", "Dana Reyes", "dana@halcyongoods.com",
         "Waxed canvas bags and small leather goods, sold direct and through about forty "
         "independent shops across the Pacific Northwest.",
         "We've been through two trading companies who both quoted us a factory price and then "
         "added their own on top. We want to talk to the people actually making the bags, and we "
         "want a partner for the whole line, not one SKU.",
         "APPROVED", "Brand selling my own products", "3–10 years", "$250k – $1M"),
        ("MMI-A-1002", 4, "Grit & Grain Coffee", "Marcus Webb", "marcus@gritgrain.co",
         "Single-origin coffee, roasted in Seattle, sold in our two cafés and by subscription.",
         "Our packaging costs more than the coffee inside it. We reorder the same bags every eight "
         "weeks and would rather build that relationship once and stop re-quoting it forever.",
         "APPROVED", "Brand selling my own products", "3–10 years", "$50k – $250k"),
        ("MMI-A-1003", 3, "Verano Skincare", "Lucia Ortiz", "lucia@veranoskin.com",
         "Clean skincare — serums and moisturisers — sold DTC and in about a dozen spas in Florida.",
         "We're relaunching the whole line in new packaging next spring and we need someone who "
         "will sample properly before running 10,000 units. Our last supplier wouldn't.",
         "INTERVIEW_SCHEDULED", "Brand selling my own products", "1–3 years", "$50k – $250k"),
        ("MMI-A-1004", 2, "Northfield Outfitters", "Sam Iyer", "sam@northfieldout.com",
         "Outdoor gear — packs, cubes, small hardware — sold online and at trade shows.",
         "We're small but growing and we're tired of MOQs that assume we're not. We'd rather find "
         "one manufacturer now and grow into them than switch every year.",
         "SUBMITTED", "Brand selling my own products", "1–3 years", "Under $50k a year"),
        ("MMI-A-1005", None, "Lumen Retail Group", "Owen Fitzgerald", "owen@lumenretail.example",
         "We buy for a group of gift shops.",
         "Looking for the cheapest possible source for a one-off promotional run.",
         "DECLINED", "Retailer", "Over 10 years", "Just getting started"),
    ]
    for (ref, cust, company_name, contact, email, sells, why, status, btype, years, volume) in applications:
        execute(
            "INSERT INTO applications (ref, customer_id, company_name, contact_name, email, "
            "business_type, years_trading, what_they_sell, why, annual_volume, availability, "
            "status, interview_at, reviewer, decided_at, decision_reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ref, cust, company_name, contact, email, btype, years, sells, why, volume,
             "Weekday mornings, US Pacific", status,
             _ts(days=2, hours=3) if status == "INTERVIEW_SCHEDULED" else None,
             "Tyler Monti" if status != "SUBMITTED" else None,
             _ts(days=-118) if status == "APPROVED" else (_ts(days=-6) if status == "DECLINED" else None),
             "Clear about what they're building and in it for the long haul."
             if status == "APPROVED" else
             ("One-off promotional buy with no follow-on line — not what we're set up for."
              if status == "DECLINED" else None),
             _ts(days=-120) if status == "APPROVED" else _ts(days=-3)))

    for cid, email, name in ((1, "dana@halcyongoods.com", "Dana Reyes"),
                             (4, "marcus@gritgrain.co", "Marcus Webb")):
        create_user(email, "member2026", name=name, role="CLIENT", customer_id=cid)

    # --- Client 1–5: accepted members with nothing assigned to them yet.
    #     Their portals are quote-only — no catalogue, just the request form. ---
    # Demo accounts. The names are placeholders for testing — swap them before
    # anyone outside the team sees this, since a real person's name on a customer
    # record reads as a real customer.
    quote_only = [
        ("Serena Williams", "Serena Williams", "Palm Beach Gardens", "United States", 16),
        ("Keanu Reeves",    "Keanu Reeves",    "Los Angeles",        "United States", 10),
        ("Zendaya",         "Zendaya",         "Oakland",            "United States", 10),
        ("Idris Elba",      "Idris Elba",      "London",             "United Kingdom", 10),
        ("Rihanna",         "Rihanna",         "Bridgetown",         "Barbados",       10),
    ]
    client_ids = []
    for i, (name, contact, city, country, limit) in enumerate(quote_only, start=1):
        ref = next_ref("MMI-C", "customers", start=1001)
        login = f"client{i}"
        cid = execute(
            "INSERT INTO customers (ref, company_name, contact_name, email, phone, country, city, "
            "stage, source, owner, tags, membership_status, member_since, quote_limit, "
            "quote_cycle_days, membership_note, address) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 'WEBSITE', 'Tyler Monti', 'quote-only', "
            "'MEMBER', ?, ?, 30, ?, ?)",
            (ref, name, contact, f"{login}@montimakesit.com", f"+1 555 010{i}",
             country, city, _ts(days=-(140 - i * 17)), limit,
             "Raised to 16 — develops a full line each season." if limit == 16 else None,
             "1200 Industrial Way\nSuite 400"))
        client_ids.append(cid)
        create_user(login, CLIENT_PASSWORD, name=contact, role="CLIENT", customer_id=cid)
        execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
                "VALUES (?, 'SYSTEM', ?, 'system')",
                (cid, "Accepted as a member — quote-only account, no catalogue assigned"))

    # A few quote requests each, so their portals and the CRM have something in them.
    quote_only_projects = [
        "Waxed canvas tote, 18L", "Kraft coffee pouch with valve", "Anodized carabiner",
        "Airless pump bottle, 50ml", "Recycled ripstop packing cubes", "Solid oak side table",
        "Powder-coated shelf bracket", "Silicone gasket set, 60mm", "Rigid magnetic-close box",
        "Stainless growler, 64oz", "Leather card holder", "Ceramic pour-over dripper",
    ]
    counts = [4, 2, 3, 2, 1]
    p_index = 0
    q_seq = 5000          # own series, so it can't collide with the demo book above
    for cid, count in zip(client_ids, counts):
        for j in range(count):
            age = 2 + j * 6
            status = "ESTIMATE_SENT" if j == 0 else ("IN_REVIEW" if j % 2 else "NEW")
            q_seq += 1
            q_ref = f"MMI-Q-{q_seq}"
            execute(
                "INSERT INTO quotes (ref, customer_id, title, description, category, quantity, "
                "status, due_at, created_at, destination_country, incoterm, responded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'United States', 'DDP', ?)",
                (q_ref, cid, quote_only_projects[p_index % len(quote_only_projects)],
                 "Submitted from the member portal. Full spec discussed on the call.",
                 "Something else", [500, 2500, 5000, 10000][j % 4], status,
                 _ts(days=-age, hours=1), _ts(days=-age),
                 _ts(days=-age + 1) if status == "ESTIMATE_SENT" else None))
            p_index += 1

    sla = current_app.config["QUOTE_SLA_HOURS"]
    quotes = [
        # ref, customer, title, description, category, qty, target, status, due, created
        ("MMI-Q-1001", 1, "Waxed canvas tote, 18L",
         "Heavyweight waxed canvas tote with leather handles and a brass hardware set. "
         "We want the body in a 18oz waxed duck, natural veg-tan leather straps, and an interior "
         "zip pocket. Reference photos attached. This is our hero SKU for fall.",
         "Bags & leather goods", 2500, 2800, "ACCEPTED", _ts(days=-9), _ts(days=-10)),
        ("MMI-Q-1002", 4, "Kraft coffee bag, 12oz, valve",
         "Recyclable kraft stand-up pouch with a one-way degassing valve and a resealable tin tie. "
         "Two-color flexo print. Need FDA food-contact compliance.",
         "Packaging & print", 25000, 32, "ACCEPTED", _ts(days=-20), _ts(days=-21)),
        ("MMI-Q-1003", 3, "Airless pump bottle, 50ml, frosted",
         "Frosted PP airless pump bottle, 50ml, with a matte gold collar. Need to match the "
         "Pantone on our existing line and pass a drop test. Sampling required before we commit.",
         "Injection molded plastics", 10000, 145, "ESTIMATE_SENT", _ts(days=-1), _ts(days=-2)),
        ("MMI-Q-1004", 2, "Anodized aluminum carabiner, custom profile",
         "Custom-profile 6061 aluminum carabiner, hard anodized matte black, laser-etched logo. "
         "Not load-rated — accessory use. CAD attached.",
         "Metal & machined parts", 5000, 210, "IN_REVIEW", plus_hours(6), _ts(hours=-18)),
        ("MMI-Q-1005", 5, "Solid oak side table, flat-pack",
         "Solid white oak side table, 45cm diameter, three-leg splay, flat-packed with a cam-lock "
         "assembly. FSC certification required for the UK market.",
         "Furniture & fixtures", 800, 5400, "NEW", plus_hours(19), _ts(hours=-5)),
        ("MMI-Q-1006", 2, "Recycled ripstop packing cubes, 3-set",
         "Set of three packing cubes in recycled ripstop with YKK zips and mesh tops. "
         "Need a GRS certificate for the recycled content claim.",
         "Apparel & textiles", 3000, 480, "NEW", plus_hours(2), _ts(hours=-22)),
    ]
    for (ref, cust, title, desc, cat, qty, target, status, due, created) in quotes:
        execute(
            "INSERT INTO quotes (ref, customer_id, title, description, category, quantity, "
            "target_unit_price_cents, status, due_at, created_at, destination_country, "
            "destination_city, incoterm, responded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DDP', ?)",
            (ref, cust, title, desc, cat, qty, target, status, due, created,
             "United States", "Los Angeles",
             _ts(days=-1) if status in ("ESTIMATE_SENT", "ACCEPTED") else None))

    estimates = [
        # quote_id, unit, qty, tooling, sample, ship, duties, lead, method
        (1, 3120, 2500, 0, 18000, 214000, 62000, 38, "SEA"),
        (2, 38, 25000, 45000, 12000, 128000, 41000, 30, "SEA"),
        (3, 168, 10000, 380000, 24000, 96000, 38000, 45, "SEA"),
    ]
    for (qid, unit, qty, tooling, sample, ship, duties, lead, method) in estimates:
        total = unit * qty + tooling + sample + ship + duties
        execute(
            "INSERT INTO estimates (quote_id, unit_price_cents, moq, quantity, tooling_cents, "
            "sample_cents, shipping_cents, duties_cents, lead_time_days, ship_method, incoterm, "
            "valid_until, notes, total_cents, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DDP', ?, ?, ?, ?, ?)",
            (qid, unit, qty, qty, tooling, sample, ship, duties, lead, method,
             (utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
             "Price holds at this quantity. A 20% volume increase takes roughly 6% off the unit.",
             total, ADMIN_EMAIL, _ts(days=-1)))

    catalog = [
        ("MMI-2001", "Waxed canvas tote, 18L", "Bags & leather goods",
         "18oz waxed duck body, veg-tan leather handles, brass hardware, interior zip pocket.",
         "18oz waxed cotton duck, vegetable-tanned leather, solid brass", 3120, 500, 38,
         "bags, leather"),
        ("MMI-2002", "Kraft coffee bag, 12oz, valve", "Packaging & print",
         "Recyclable kraft stand-up pouch, one-way degassing valve, resealable tin tie, 2-color flexo.",
         "Kraft paper / PLA liner", 38, 10000, 30, "packaging, food-safe"),
        ("MMI-2003", "Matte black cold brew growler, 64oz", "Metal & machined parts",
         "Double-walled stainless growler, matte powder coat, screw cap with silicone gasket.",
         "304 stainless steel", 1840, 500, 35, "drinkware, metal"),
        ("MMI-2004", "Recycled mailer, 10×13, padded", "Packaging & print",
         "100% recycled padded mailer with a tear strip and a double adhesive return seal.",
         "Recycled kraft, recycled paper padding", 41, 20000, 24, "packaging, shipping"),
        ("MMI-2005", "Leather card holder, 4-slot", "Bags & leather goods",
         "Four-slot card holder in veg-tan leather, saddle-stitched, debossed logo.",
         "Vegetable-tanned leather, waxed linen thread", 690, 1000, 30, "leather, accessories"),
        ("MMI-2006", "Rigid box, magnetic close", "Packaging & print",
         "1200gsm greyboard rigid box with a magnetic closure and soft-touch lamination.",
         "1200gsm greyboard, soft-touch film", 212, 2000, 32, "packaging, retail"),
    ]
    for row in catalog:
        execute(
            "INSERT INTO catalog_items (sku, name, category, description, materials, "
            "unit_price_cents, moq, lead_time_days, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)

    execute("UPDATE customers SET catalog_tags = ? WHERE ref = 'MMI-C-1001'", ("bags, leather",))
    execute("UPDATE customers SET catalog_tags = ? WHERE ref = 'MMI-C-1004'", ("packaging,",))

    assignments = [
        (1, 1, 2980, 500, "Locked price through Q4 at 500+ units."),
        (3, 1, None, None, None),
        (2, 4, 36, 10000, "Volume price — 25k+ per release."),
        (4, 4, None, None, None),
    ]
    for item_id, cust_id, price, moq, note in assignments:
        execute(
            "INSERT INTO catalogue_registrations (item_id, customer_id, unit_price_cents, moq, "
            "notes, assigned_by) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, cust_id, price, moq, note, ADMIN_EMAIL))

    # --- orders in several states -------------------------------------------
    review_close = plus_hours(9)
    order_specs = [
        # ref, cust, quote, status, pay_method, pay_status, funds_at, release_at, reviewed_at,
        # reviewed_by, shipped_at, carrier, tracking, ship_cents, created
        ("MMI-O-2001", 1, 1, "SHIPPED", "ACH", "PAID", _ts(days=-8), _ts(days=-7),
         _ts(days=-7), "Tyler Monti", _ts(days=-2), "Maersk", "MAEU7742019", 276000, _ts(days=-9)),
        ("MMI-O-2002", 4, 2, "IN_PRODUCTION", "CARD", "PAID", _ts(days=-4), _ts(days=-3),
         _ts(days=-3), "Tyler Monti", None, None, None, 169000, _ts(days=-5)),
        ("MMI-O-2003", 1, None, "IN_REVIEW", "ACH", "PAID", _ts(hours=-15), review_close,
         None, None, None, None, None, 42000, _ts(hours=-16)),
        ("MMI-O-2004", 4, None, "PENDING_PAYMENT", None, "UNPAID", None, None,
         None, None, None, None, None, 0, _ts(hours=-3)),
    ]
    for (ref, cust, qid, status, method, pstatus, funds, release, reviewed, reviewer,
         shipped, carrier, tracking, ship_cents, created) in order_specs:
        execute(
            "INSERT INTO orders (ref, customer_id, source_quote_id, status, payment_method, "
            "payment_status, payment_provider, funds_confirmed_at, review_release_at, reviewed_at, "
            "reviewed_by, shipped_at, carrier, tracking_number, shipping_cents, created_at, "
            "orders_email_sent_at) VALUES (?, ?, ?, ?, ?, ?, 'mock', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ref, cust, qid, status, method, pstatus, funds, release, reviewed, reviewer,
             shipped, carrier, tracking, ship_cents, created, funds))

    order_items = [
        (1, "Waxed canvas tote, 18L", "MMI-2001", 2980, 2500),
        (1, "Sampling", "MMI-Q-1001", 18000, 1),
        (2, "Kraft coffee bag, 12oz, valve", "MMI-2002", 36, 25000),
        (2, "Tooling (one-time)", "MMI-Q-1002", 45000, 1),
        (3, "Waxed canvas tote, 18L", "MMI-2001", 2980, 600),
        (4, "Recycled mailer, 10×13, padded", "MMI-2004", 41, 20000),
    ]
    for order_id, name, sku, unit, qty in order_items:
        execute(
            "INSERT INTO order_items (order_id, name, sku, unit_price_cents, quantity, line_total_cents) "
            "VALUES (?, ?, ?, ?, ?, ?)", (order_id, name, sku, unit, qty, unit * qty))

    from .orders import fee_on
    for order_id in (1, 2, 3, 4):
        row = query("SELECT COALESCE(SUM(line_total_cents),0) AS s FROM order_items WHERE order_id = ?",
                    (order_id,), one=True)
        order = query("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        before_fee = row["s"] + order["shipping_cents"]
        fee = fee_on(before_fee)
        proc = int(round((before_fee + fee) * 0.029)) + 30
        execute("UPDATE orders SET subtotal_cents = ?, fee_cents = ?, processing_fee_cents = ?, "
                "total_cents = ? WHERE id = ?",
                (row["s"], fee, proc, before_fee + fee + proc, order_id))
        execute("UPDATE customers SET lifetime_value_cents = lifetime_value_cents + ? WHERE id = ?",
                (before_fee + fee if order["payment_status"] == "PAID" else 0,
                 order["customer_id"]))

    events_by_order = {
        1: [("ORDER_CREATED", "Converted from MMI-Q-1001"), ("FUNDS_CONFIRMED", "ACH funds confirmed"),
            ("ORDERS_EMAIL_SENT", "Sent to orders@montimakesit.com"),
            ("REVIEW_APPROVED", "Specs verified against the approved sample"),
            ("SHIPPED", "Maersk MAEU7742019")],
        2: [("ORDER_CREATED", "Converted from MMI-Q-1002"), ("FUNDS_CONFIRMED", "Card funds confirmed"),
            ("ORDERS_EMAIL_SENT", "Sent to orders@montimakesit.com"),
            ("REVIEW_APPROVED", "Valve spec confirmed with the supplier")],
        3: [("ORDER_CREATED", "Reorder from private catalog"), ("FUNDS_CONFIRMED", "ACH funds confirmed"),
            ("ORDERS_EMAIL_SENT", "Sent to orders@montimakesit.com")],
        4: [("ORDER_CREATED", "Reorder from private catalog")],
    }
    for order_id, events in events_by_order.items():
        for event, detail in events:
            execute("INSERT INTO order_events (order_id, event, detail, actor) VALUES (?, ?, ?, 'system')",
                    (order_id, event, detail))

    activities = [
        (1, "CALL", "Walked through the leather grade options. Dana wants veg-tan, no shortcuts."),
        (1, "EMAIL", "Sent estimate on MMI-Q-1001 — $10,714.00"),
        (2, "NOTE", "Seasonal buyer — plans two drops a year. Worth locking a calendar reminder in June."),
        (3, "MEETING", "Video call on the airless pump. They need a physical sample before committing."),
        (4, "NOTE", "Reorders roughly every 8 weeks. Good candidate for a standing PO."),
        (5, "EMAIL", "Cold intro sent, no reply yet. Follow up in two weeks."),
        (2, "SYSTEM", "Submitted membership application MMI-A-1004"),
        (3, "MEETING", "Membership interview booked — video call in two days."),
    ]
    for cid, kind, body in activities:
        execute("INSERT INTO crm_activities (customer_id, kind, body, author) VALUES (?, ?, ?, ?)",
                (cid, kind, body, ADMIN_EMAIL))

    events = [
        ("Membership interview · Verano Skincare", 3, "INTERVIEW", _ts(days=2, hours=3), "Zoom"),
        ("Call — Verano sampling plan", 3, "CALL", _ts(days=1, hours=2), "Zoom"),
        ("Factory walk — tote line", 1, "FACTORY", _ts(days=2), "Dongguan plant"),
        ("Review deadline · MMI-O-2003", 1, "DEADLINE", review_close, None),
        ("Shipment ETA — MMI-O-2001", 1, "SHIPMENT", _ts(days=12), "Port of Long Beach"),
        ("Follow up — Solace Home", 5, "FOLLOWUP", _ts(days=4), None),
        ("Quarterly check-in — Grit & Grain", 4, "MEETING", _ts(days=6, hours=3), "Zoom"),
        ("Quote due · MMI-Q-1005", 5, "DEADLINE", plus_hours(19), None),
    ]
    for title, cid, kind, starts, location in events:
        execute(
            "INSERT INTO calendar_events (title, customer_id, kind, starts_at, location, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)", (title, cid, kind, starts, location, ADMIN_EMAIL))

    # --- Client 1 is the worked example: one product they can actually buy.
    #     Clients 2-5 stay quote-only, so both states are visible side by side. ---
    client1 = client_ids[0]
    c1_sku = "MMI-3001"
    c1_item = execute(
        "INSERT INTO catalog_items (sku, name, category, description, specs, materials, "
        "unit_price_cents, moq, lead_time_days, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (c1_sku, f"Waxed canvas tote, 18L — {quote_only[0][0]} edition", "Bags & leather goods",
         "The tote we built for Client 1: 18oz waxed duck body, vegetable-tanned leather handles, "
         "solid brass hardware, interior zip pocket, debossed logo on the base panel.",
         "360 x 400 x 140 mm\nMatte brass hardware\nInterior zip pocket, 200 x 140 mm\n"
         "Debossed logo, base panel",
         "18oz waxed cotton duck, vegetable-tanned leather, solid brass", 2980, 250, 34,
         "client-1"))
    execute("UPDATE customers SET catalog_tags = 'client-1', freight_waived_default = 1 "
            "WHERE id = ?", (client1,))
    execute(
        "INSERT INTO catalogue_registrations (item_id, customer_id, unit_price_cents, moq, "
        "notes, assigned_by) VALUES (?, ?, ?, ?, ?, 'Tyler Monti')",
        (c1_item, client1, 2980, 250,
         "Locked at $29.80 through Q4 at 250+ units. Reorder any time."))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
            "VALUES (?, 'SYSTEM', ?, 'Tyler Monti')",
            (client1, f"Catalog item {c1_sku} assigned — first product they can order directly"))

    # --- a few requests sitting in the incoming queue, waiting to be triaged ---
    incoming = [
        (client_ids[1], "Ceramic pour-over dripper, 2-cup",
         "Stoneware dripper with a 60-degree cone, matte white glaze, our logo on the base. "
         "We sell about 400 a month and want to bring it in-house.", 3000, 4),
        (client_ids[2], "Aluminium travel tin, 90mm",
         "Shallow screw-top tin, matte black anodize, food-safe liner. Replacing a supplier who "
         "kept missing tolerances on the thread.", 8000, 9),
        (client_ids[4], "Cotton drawstring dust bag",
         "Unbleached cotton dust bag, 30x40cm, single-colour screen print. Goes in the box with "
         "every order we ship.", 15000, 20),
    ]
    for cid, title, desc, qty, hours_ago in incoming:
        q_seq += 1
        execute(
            "INSERT INTO quotes (ref, customer_id, title, description, category, quantity, "
            "status, due_at, created_at, destination_country, incoterm) "
            "VALUES (?, ?, ?, ?, 'Something else', ?, 'NEW', ?, ?, 'United States', 'DDP')",
            (f"MMI-Q-{q_seq}", cid, title, desc, qty,
             _ts(hours=24 - hours_ago), _ts(hours=-hours_ago)))

    # --- a year of confirmed orders, so the revenue dashboard has real history ---
    import random
    rng = random.Random(20260826)
    order_seq = 3000
    for back in range(364, -1, -1):
        day = utcnow() - timedelta(days=back)
        weekday = day.weekday()
        growth = 0.55 + 0.45 * ((365 - back) / 365)
        weekend = 0.22 if weekday >= 5 else 1.0
        expected = 2.1 * growth * weekend
        n = int(expected) + (1 if rng.random() < (expected % 1) else 0)
        for _ in range(n):
            cid = rng.choice(client_ids)
            goods = rng.randint(180000, 1580000)
            if rng.random() > 0.9:
                goods += rng.randint(0, 3600000)
            fee = fee_on(goods)
            proc = int(round((goods + fee) * 0.029)) + 30
            total = goods + fee + proc
            confirmed = day.replace(hour=rng.randint(8, 19), minute=rng.randint(0, 59),
                                    second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
            order_seq += 1
            oid = execute(
                "INSERT INTO orders (ref, customer_id, status, subtotal_cents, fee_cents, "
                "processing_fee_cents, total_cents, "
                "payment_method, payment_status, payment_provider, funds_confirmed_at, "
                "review_release_at, reviewed_at, reviewed_by, production_started_at, shipped_at, "
                "delivered_at, created_at, orders_email_sent_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PAID', 'stripe', ?, ?, ?, 'Tyler Monti', ?, ?, ?, ?, ?)",
                (f"MMI-O-{order_seq}", cid,
                 "DELIVERED" if back > 30 else ("SHIPPED" if back > 3 else "IN_PRODUCTION"),
                 goods, fee, proc, total, rng.choice(["CARD", "ACH", "WIRE"]), confirmed,
                 (day + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                 (day + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                 (day + timedelta(days=1, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                 (day + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S") if back > 3 else None,
                 (day + timedelta(days=22)).strftime("%Y-%m-%d %H:%M:%S") if back > 30 else None,
                 confirmed, confirmed))
            execute(
                "INSERT INTO order_items (order_id, name, sku, unit_price_cents, quantity, "
                "line_total_cents) VALUES (?, ?, ?, ?, 1, ?)",
                (oid, "Custom production run", f"MMI-O-{order_seq}", goods, goods))
            execute("UPDATE customers SET lifetime_value_cents = lifetime_value_cents + ? WHERE id = ?",
                    (total, cid))

    # Give a few of the historic orders real tracking codes, so the client timeline
    # has something to show.
    for i, row in enumerate(query("SELECT id, ref FROM orders WHERE status IN "
                                  "('SHIPPED','DELIVERED') ORDER BY id DESC LIMIT 20")):
        execute("UPDATE orders SET carrier = ?, tracking_number = ? WHERE id = ?",
                (["Maersk", "DHL Express", "FedEx", "ONE"][i % 4],
                 f"MMI{row['ref'].split('-')[-1]}{1000 + i * 37}", row["id"]))

    print("Seeded.")
    print(f"  Admin:   {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Clients: client1 … client5 / {CLIENT_PASSWORD}")
    for i, (name, *_rest) in enumerate(quote_only, start=1):
        print(f"           client{i} = {name}")
    print("  Members: dana@halcyongoods.com / member2026")
    print("           marcus@gritgrain.co / member2026")

    _mark_fixtures()
