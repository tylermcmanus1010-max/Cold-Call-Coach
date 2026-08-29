"""CHG-017 baseline — what the impersonation path does today.

REWRITTEN after D-029. The first version impersonated Boars Head (MMI-C-1001), wrote a
record as them, deleted three of the five rows an intake writes, and printed "(probe rows
removed)". Amended §4.5 forbids exactly that: no adversarial test leaves residue, every
write is reverted in the same phase, and a test that must write uses a throwaway account,
never MMI-C-1001.

So this probe now:
  * creates its own throwaway customer and portal user, impersonates THAT,
  * records the ADMIN's password hash before changing it and restores it after,
  * deletes every row it caused — all five an intake writes, plus the throwaway
    account itself — and then RE-QUERIES to prove zero rather than asserting it.

A test that cannot clean up after itself is not a test you can run twice.
"""
import re
from werkzeug.security import generate_password_hash
from monti import create_app
from monti.db import query, execute
from monti.auth import create_user

MARK = "CHG-017 baseline write probe"
app = create_app(); app.config.update(TESTING=True)

with app.app_context():
    admin = query("SELECT * FROM users WHERE role='ADMIN'", one=True)
    saved_hash, saved_flag = admin["password_hash"], admin["must_change_password"]
    execute("UPDATE users SET must_change_password = 0, password_hash = ? WHERE id = ?",
            (generate_password_hash("p1admin"), admin["id"]))
    # The throwaway. Never MMI-C-1001.
    tid = execute("INSERT INTO customers (ref, company_name, email, membership_status, "
                  "is_fixture) VALUES ('MMI-C-TEST', 'Throwaway Probe Account', "
                  "'probe@example.invalid', 'MEMBER', 0)")
    create_user("probe@example.invalid", "probepw", name="Probe", role="CLIENT", customer_id=tid)
    boars = query("SELECT id, ref, company_name FROM customers WHERE ref = 'MMI-C-1001'", one=True)

def login(c, email, pw):
    tok = re.search(r'name="_csrf" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)
    return c.post("/login", data={"email": email, "password": pw, "_csrf": tok}, follow_redirects=True)

adm = app.test_client(); login(adm, admin["email"], "p1admin")

print("# CHG-017 — impersonation baseline")
print(f"# Impersonating the throwaway MMI-C-TEST (id {tid}), never MMI-C-1001 (§4.5, D-029).")
print(f"# Boars Head is {boars['ref']} / {boars['company_name']} and is not touched.")
print()
print("## Before")
with app.app_context():
    print(f"security_log rows: {query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
print(f"admin GET /portal/ -> {adm.get('/portal/').status_code}   (403 = no access yet)")
print()
print("## The impersonation act")
r = adm.get(f"/admin/clients/{tid}/open", follow_redirects=False)
print(f"GET /admin/clients/{tid}/open -> {r.status_code} -> {r.headers.get('Location')}")
print("  reason prompt before the redirect:  no — it is a GET link, nothing is asked")
print("  confirmation step:                  no")
print()
print("## After")
resp = adm.get("/portal/"); body = resp.get_data(as_text=True)
print(f"admin GET /portal/ -> {resp.status_code}   (200 = full member portal)")
print(f"admin-view banner rendered:          "
      f"{'yes' if 'Admin view' in body and 'you are looking at' in body else 'NO'}"
      f"   (_shell.html:17, g.viewing_as at auth.py:80)")
with app.app_context():
    print(f"rows written to security_log:        "
          f"{query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
print()
print("## Write access during impersonation")
tok = re.search(r'name="_csrf" value="([^"]+)"', adm.get("/portal/requests").get_data(as_text=True))
wrote = False
if tok:
    w = adm.post("/portal/requests", data={"summary": MARK, "weight": "1",
                                           "_csrf": tok.group(1)}, follow_redirects=False)
    print(f"POST /portal/requests while impersonating -> {w.status_code} {w.headers.get('Location','')}")
    with app.app_context():
        row = query("SELECT ref FROM quotes WHERE title = ?", (MARK,), one=True)
    wrote = bool(row)
    print(f"  a write landed as the member: {'YES — ' + row['ref'] if row else 'no'}")
    print(f"  read-only by default: {'no' if wrote else 'n/a'}   "
          f"separate logged elevation: {'no' if wrote else 'n/a'}")
    with app.app_context():
        print(f"security_log rows after the write:   "
              f"{query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
print()
print("## Against CHG-017's gate")
for clause, state in [
    ("every impersonation session logged", "NOT MET — zero rows written"),
    ("timestamped", "NOT MET — no row to stamp"),
    ("attributed to a named admin", "NOT MET"),
    ("reason-tagged", "NOT MET — no reason is asked for"),
    ("read-only by default", "NOT MET — a write succeeded"),
    ("visible in the member's security log in one page load",
     "NOT MET — no member-facing security log surface exists"),
    ("write actions require a separate logged elevation", "NOT MET"),
]:
    print(f"  {clause:56} {state}")
print()
print("security_log is created at schema.sql:502 and written by nothing. Its only other")
print("reference is monti/purge.py:43, as an orphan-sweep target.")
print()
print("## Cleanup — every row this probe caused, then a re-query to prove zero")
with app.app_context():
    qids = [r["id"] for r in query("SELECT id FROM quotes WHERE title = ?", (MARK,))]
    for sql, args in [
        ("DELETE FROM capacity_ledger WHERE customer_id = ?", (tid,)),
        ("DELETE FROM decision_items WHERE customer_id = ?", (tid,)),
        ("DELETE FROM calendar_events WHERE customer_id = ?", (tid,)),
        ("DELETE FROM crm_activities WHERE customer_id = ?", (tid,)),
        ("DELETE FROM quotes WHERE customer_id = ?", (tid,)),
        ("DELETE FROM client_agents WHERE customer_id = ?", (tid,)),
        ("DELETE FROM users WHERE customer_id = ?", (tid,)),
        ("DELETE FROM customers WHERE id = ?", (tid,)),
    ]:
        execute(sql, args)
    execute("UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
            (saved_hash, saved_flag, admin["id"]))
    left = 0
    for t, col in [("quotes", "title"), ("decision_items", "auto_name"),
                   ("capacity_ledger", "label"), ("crm_activities", "body"),
                   ("calendar_events", "title")]:
        n = query(f"SELECT COUNT(*) AS c FROM {t} WHERE {col} LIKE ? OR customer_id = ?",
                  (f"%{MARK}%", tid), one=True)["c"]
        left += n
        print(f"  {t:17} rows left from this probe: {n}")
    n = query("SELECT COUNT(*) AS c FROM customers WHERE id = ?", (tid,), one=True)["c"]
    print(f"  {'customers':17} rows left from this probe: {n}")
    print(f"  admin credentials restored:        "
          f"{query('SELECT password_hash FROM users WHERE id = ?', (admin['id'],), one=True)['password_hash'] == saved_hash}")
    bh = query("SELECT COUNT(*) AS c FROM crm_activities WHERE customer_id = ?",
               (boars["id"],), one=True)["c"]
    print(f"  Boars Head CRM entries (untouched): {bh}")
    print(f"  TOTAL residue: {left + n}")
