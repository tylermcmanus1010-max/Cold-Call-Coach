"""Render every GET surface as anonymous, as the member and as admin.

Session-mutating routes are held out of the sweep: GETting /logout mid-sweep signs the
client out and every later row reads as anonymous, which looks exactly like a gating
defect and is not one. They are probed separately at the end, and those probes are the
CHG-017 baseline.

Needs a launched database plus a member user (the launch creates the admin only).
"""
import re
from werkzeug.security import generate_password_hash
from monti import create_app
from monti.db import query, execute
from monti.auth import create_user

app = create_app(); app.config.update(TESTING=True)
with app.app_context():
    cust = query("SELECT * FROM customers", one=True)
    execute("UPDATE users SET must_change_password = 0, password_hash = ? WHERE role='ADMIN'",
            (generate_password_hash("p1admin"),))
    admin = query("SELECT * FROM users WHERE role='ADMIN'", one=True)
    if not query("SELECT id FROM users WHERE customer_id = ?", (cust["id"],), one=True):
        create_user(cust["email"], "p1pass", name="Member", role="CLIENT",
                    customer_id=cust["id"])
    item = query("SELECT * FROM catalog_items LIMIT 1", one=True)
    ditem = query("SELECT * FROM decision_items LIMIT 1", one=True)

def login(c, email, pw):
    tok = re.search(r'name="_csrf" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)
    return c.post("/login", data={"email": email, "password": pw, "_csrf": tok},
                  follow_redirects=True)

HELD_OUT = {"auth.logout", "admin.open_client", "admin.close_client", "auth.login"}
anon = app.test_client()
member = app.test_client(); r1 = login(member, cust["email"], "p1pass")
adm = app.test_client();    r2 = login(adm, admin["email"], "p1admin")

subs = {"int:item_id": str(item["id"]) if item else "1", "int:customer_id": str(cust["id"]),
        "int:order_id": "1", "int:quote_id": "1", "int:app_id": "1", "int:cart_id": "1",
        "int:event_id": "1", "int:file_id": "1",
        "ref": ditem["ref"] if ditem else "MMI-D-001",
        "sku": item["sku"] if item else "MMI-B-0101",
        "receipt_no": "MMI-R-100001", "path:filename": "css/app.css", "action": "accept"}
fill = lambda rule: re.sub(r"<([^>]+)>", lambda m: subs.get(m.group(1), "1"), rule)

rules = sorted([r for r in app.url_map.iter_rules()
                if "GET" in r.methods and r.endpoint != "static" and r.endpoint not in HELD_OUT],
               key=lambda r: (r.endpoint.split(".")[0], str(r.rule)))

print("# Render census — every GET surface, three viewers, real responses through the app")
print(f"# {len(rules)} GET routes swept")
print(f"# member login {'OK' if b'Boars Head' in r1.data else 'CHECK'} · admin login "
      f"{'OK' if r2.status_code == 200 else 'CHECK'}")
print("# held out because they mutate the session, probed separately below:")
print("#   " + ", ".join(sorted(HELD_OUT)))
print()
print(f"{'route':44} {'anon':>4} {'mbr':>4} {'adm':>4}  {'signout':>7} {'money$':>6} {'chart':>5}")
print("-" * 90)

def counts(resp):
    if resp.status_code != 200:
        return "", "", ""
    b = resp.get_data(as_text=True)
    return (str(b.count("Sign out")), str(len(re.findall(r"\$[\d,]+\.\d\d", b))),
            "yes" if ("chart-svg" in b or "spark" in b) else "")

once = zero = unmeasured = twice = 0
ok200 = 0
for r in rules:
    url = fill(str(r.rule))
    ra, rm, rd = anon.get(url), member.get(url), adm.get(url)
    so_m, mo_m, ch_m = counts(rm)
    so_a, mo_a, ch_a = counts(rd)
    so = so_a or so_m
    if so == "": unmeasured += 1
    elif int(so) == 0: zero += 1
    elif int(so) == 1: once += 1
    else: twice += 1
    if 200 in (rm.status_code, rd.status_code): ok200 += 1
    print(f"{url:44} {ra.status_code:>4} {rm.status_code:>4} {rd.status_code:>4}  "
          f"{so:>7} {(mo_a or mo_m):>6} {(ch_a or ch_m):>5}")

print()
print(f"GET surfaces swept: {len(rules)} · rendered 200 for at least one viewer: {ok200}")
print(f"'Sign out' per surface — once: {once} · zero: {zero} · unmeasured: {unmeasured} "
      f"· MORE THAN ONCE: {twice}")
print("  The 'zero' surfaces are the public pages, the password page and the two CSV")
print("  exports — none of which loads the shell that carries the control.")

print()
print("## Held-out probes")
r = adm.get(f"/admin/clients/{cust['id']}/open", follow_redirects=False)
print(f"GET /admin/clients/{cust['id']}/open -> {r.status_code} {r.headers.get('Location')}")
with app.app_context():
    print(f"  rows written to security_log: {query('SELECT COUNT(*) AS c FROM security_log', one=True)['c']}")
resp = adm.get("/portal/")
body = resp.get_data(as_text=True)
print(f"  admin now sees the member portal: {resp.status_code}")
print(f"  admin-view banner rendered: {'YES' if 'Admin view' in body else 'NO'} "
      f"(_shell.html:17, g.viewing_as at auth.py:80)")
print(f"GET /admin/clients/close -> {adm.get('/admin/clients/close', follow_redirects=False).status_code}")
r = member.get("/logout", follow_redirects=False)
print(f"GET /logout (member) -> {r.status_code} {r.headers.get('Location')}")
print(f"  after logout, GET /portal/ -> {member.get('/portal/').status_code} (expect 302)")
