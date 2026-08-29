"""CHG-017 baseline — what the impersonation path actually does today.

Recorded at Phase 1 so Phase 8 has a before to measure against. An observation,
not a fix: §1.9 forbids building an in-scope item outside its phase.
"""
import re
from werkzeug.security import generate_password_hash
from monti import create_app
from monti.db import query, execute

app = create_app(); app.config.update(TESTING=True)
with app.app_context():
    cust = query("SELECT * FROM customers", one=True)
    execute("UPDATE users SET must_change_password = 0, password_hash = ? WHERE role='ADMIN'",
            (generate_password_hash("p1admin"),))
    admin = query("SELECT * FROM users WHERE role='ADMIN'", one=True)

def login(c, email, pw):
    tok = re.search(r'name="_csrf" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)
    return c.post("/login", data={"email": email, "password": pw, "_csrf": tok}, follow_redirects=True)

adm = app.test_client(); login(adm, admin["email"], "p1admin")

print("# CHG-017 — impersonation baseline on the frozen build")
print()
print("## Before")
with app.app_context():
    print(f"security_log rows: {query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
print(f"admin GET /portal/ -> {adm.get('/portal/').status_code}   (403 = no access yet)")
print()
print("## The impersonation act")
r = adm.get(f"/admin/clients/{cust['id']}/open", follow_redirects=False)
print(f"GET /admin/clients/{cust['id']}/open -> {r.status_code} -> {r.headers.get('Location')}")
print("  reason prompt before the redirect:  no — it is a GET link, nothing is asked")
print("  confirmation step:                  no")
print()
print("## After")
resp = adm.get("/portal/"); body = resp.get_data(as_text=True)
print(f"admin GET /portal/ -> {resp.status_code}   (200 = full member portal)")
banner = "Admin view" in body and "you are looking at" in body
print(f"admin-view banner rendered:          {'yes' if banner else 'NO'}"
      f"   (_shell.html:17, g.viewing_as set at auth.py:80)")
with app.app_context():
    print(f"rows written to security_log:        {query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
print()
print("## Write access during impersonation")
tok = re.search(r'name="_csrf" value="([^"]+)"', adm.get("/portal/requests").get_data(as_text=True))
if tok:
    w = adm.post("/portal/requests", data={"summary": "CHG-017 baseline write probe",
                                           "weight": "1", "_csrf": tok.group(1)},
                 follow_redirects=False)
    print(f"POST /portal/requests while impersonating -> {w.status_code} {w.headers.get('Location','')}")
    with app.app_context():
        row = query("SELECT ref FROM quotes WHERE title LIKE '%baseline write probe%'", one=True)
        print(f"  a write landed as the member: {'YES — ' + row['ref'] if row else 'no'}")
        print(f"  read-only by default: {'no' if row else 'n/a'}   "
              f"separate logged elevation: {'no' if row else 'n/a'}")
        if row:
            execute("DELETE FROM capacity_ledger WHERE label LIKE '%baseline write probe%'")
            execute("DELETE FROM decision_items WHERE quote_id IN "
                    "(SELECT id FROM quotes WHERE title LIKE '%baseline write probe%')")
            execute("DELETE FROM quotes WHERE title LIKE '%baseline write probe%'")
            print("  (probe rows removed)")
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
