import re
from pathlib import Path
from werkzeug.security import generate_password_hash
from monti import create_app
from monti.db import query, execute

LINK_BEFORE_BAR = re.compile(r'<a[^>]*>\s*<rect class="chart-bar"')
CSS_RULE = re.compile(r'\.([a-z-]*(?:share|track|fill)[a-z-]*)\s*\{')

print("# Charting baseline on the frozen build")
print()
print("## Is there a charting layer?")
js = sorted(p.name for p in Path("monti/static/js").glob("*.js"))
print("  static/js files:", js)
chartjs = [n for n in js if "chart" in n.lower()]
print("  a chart module: ", chartjs or "NONE — no chart module of any kind")
tmpl_charts = sorted({str(p) for p in Path("monti/templates").rglob("*.html")
                      if re.search(r"<svg|chart-|sparkline|<canvas", p.read_text())})
print("  templates drawing marks inline:", len(tmpl_charts))
for t in tmpl_charts:
    print("   ", t)
print()
print("  Every chart is drawn as inline SVG inside its own template. There is no shared")
print("  renderer, so a fill-path or y-domain fix would have to be made per template —")
print("  which §1.4 calls a protocol violation. VIZ-01 builds the layer at Phase 5.")
print()

app = create_app(); app.config.update(TESTING=True)
with app.app_context():
    execute("UPDATE users SET must_change_password = 0, password_hash = ? WHERE role='ADMIN'",
            (generate_password_hash("p1admin"),))
    admin = query("SELECT * FROM users WHERE role='ADMIN'", one=True)
c = app.test_client()
tok = re.search(r'name="_csrf" value="([^"]+)"', c.get("/login").get_data(as_text=True)).group(1)
c.post("/login", data={"email": admin["email"], "password": "p1admin", "_csrf": tok},
       follow_redirects=True)
body = c.get("/admin/revenue").get_data(as_text=True)

print("## GET /admin/revenue — what the chart actually renders on real data")
bars = re.findall(r'<rect class="chart-bar"[^>]*height="([\d.]+)"', body)
print("  <rect class=\"chart-bar\"> marks:", len(bars))
print("  distinct heights:             ", len(set(bars)), " sample:", sorted(set(bars))[:8])
print("  all marks zero-height:        ", all(float(h) == 0 for h in bars) if bars else "n/a")
fills = sorted(set(re.findall(r'<rect class="chart-bar"[^>]*fill="([^"]*)"', body)))
print("  fill attribute on marks:      ", fills or "(none — filled by CSS)")
print("  hover affordance present:     ", "Hover a bar" in body)
print("  drill-down link on a mark:    ",
      "yes" if LINK_BEFORE_BAR.search(body) else "NO — marks are not links (CHG-008)")
print()
print("  Note the dataset: after launch this build holds one client and zero orders, so the")
print("  marks are honest zeroes. CHG-001's gate asks for 'seven distinct daily marks' and")
print("  'tallest equals Best Day' — see D-018; that is a property of the data, not of the")
print("  renderer, and Phase 2's degraded-surface list decides whether the gate is testable")
print("  at Phase 5 at all.")
print()
print("## Share bars (CHG-005)")
share = sorted(set(re.findall(r'class="([^"]*(?:share|bar-track|bar-fill)[^"]*)"', body)))
print("  share-bar markup on /admin/revenue:", share or "NONE FOUND by class name")
print("  client rows on the revenue screen: ", len(re.findall(r"/admin/clients/[0-9]+/open", body)))
css = Path("monti/static/css/app.css").read_text()
print("  share/track/fill rules in app.css: ", sorted(set(CSS_RULE.findall(css))) or "none")
print()
print("## Sparkline (CHG-002)")
print("  'spark' appears on /admin/revenue: ", "spark" in body)
sparks = sorted({str(p) for p in Path("monti/templates").rglob("*.html") if "spark" in p.read_text()})
print("  templates mentioning a sparkline:  ", sparks or "NONE — no sparkline exists in this build")
print()
print("## Period vocabulary (CHG-009)")
import monti.analytics as A
print("  analytics.PERIODS:", A.PERIODS)
print("  ledger vocabulary: month / quarter / year (monti/ledger.py:periods)")
print("  The revenue screen offers rolling day-windows; the ledger offers calendar")
print("  month/quarter/year. Two vocabularies over the same money — that is CHG-009.")
