"""A43 — the demo doors do not exist unless someone turned them on.

DEMO_MODE signs you into a real member account and into the admin portal with no
password. Boars Head has real orders, real negotiated prices and a real ledger;
the admin portal reaches every account there is. So the flag is the whole
security boundary, and a flag is only a boundary if it is actually checked.

The failure this catches is not exotic. It is a developer leaving the flag on, or
a later refactor moving the check from the route into the template — at which
point the button is gone from the page and the route still answers, which is
worse than leaving the button there, because now nobody can see it.

So the check runs the app with the flag OFF, which is the production posture, and
asserts three things:

  The routes are gone.   POST /demo/member and /demo/admin return 404, not 403
                         and not a redirect. The existence of a passwordless door
                         is itself information, and 403 confirms it.

  Nothing is signed in.  After those attempts, the client is still anonymous and
                         a member-only page still refuses it. A route that 404s
                         but sets the session first would pass a status check.

  The buttons are gone.  The home page carries no demo form and no link to the
                         demo routes.

Then it turns the flag ON and asserts the doors work, because a control that is
never exercised in the state it exists for is a control nobody knows is broken.
"""
import re

from . import Check, Finding

ROLES = ("member", "admin")


def _with_demo(ctx, on):
    """Flip the flag on the live app, returning the previous value."""
    was = ctx.app.config.get("DEMO_MODE")
    ctx.app.config["DEMO_MODE"] = on
    return was


def run(ctx):
    findings = []
    was = _with_demo(ctx, False)
    try:
        client = ctx.app.test_client()

        # ---- off: the routes do not answer --------------------------------
        for role in ROLES:
            with client.session_transaction() as sess:
                sess["_csrf"] = "a43-token"
            reply = client.post(f"/demo/{role}", data={"_csrf": "a43-token"})
            if reply.status_code != 404:
                findings.append(Finding(
                    f"POST /demo/{role}",
                    f"answered {reply.status_code} with DEMO_MODE off. A passwordless "
                    "door into a real account has to be absent, not refused — even a "
                    "403 confirms it is there"))
            with client.session_transaction() as sess:
                if sess.get("user_id") or sess.get("demo"):
                    findings.append(Finding(
                        f"POST /demo/{role}",
                        "signed somebody in before refusing. The status code says no "
                        "and the session says yes"))

        # ---- off: nothing reachable behind them ---------------------------
        guarded = client.get("/portal/", follow_redirects=False)
        if guarded.status_code == 200:
            findings.append(Finding(
                "GET /portal/",
                "served the member portal to a client that never signed in"))
        admin_page = client.get("/admin/", follow_redirects=False)
        if admin_page.status_code == 200:
            findings.append(Finding(
                "GET /admin/", "served the admin portal to a client that never signed in"))

        # ---- off: the buttons are not on the page -------------------------
        home = ctx.public_client.get("/", follow_redirects=True).get_data(as_text=True)
        if "/demo/" in home:
            findings.append(Finding(
                "GET /",
                "the home page still points at a demo route with DEMO_MODE off"))
        if re.search(r"demo-doors", home):
            findings.append(Finding(
                "GET /", "the demo panel renders with DEMO_MODE off"))

        # ---- on: the doors work, and say so -------------------------------
        _with_demo(ctx, True)
        for role, landing in (("member", "/portal/"), ("admin", "/admin/")):
            door = ctx.app.test_client()
            with door.session_transaction() as sess:
                sess["_csrf"] = "a43-token"
            reply = door.post(f"/demo/{role}", data={"_csrf": "a43-token"})
            if reply.status_code not in (301, 302):
                findings.append(Finding(
                    f"POST /demo/{role}",
                    f"answered {reply.status_code} with DEMO_MODE on — the door that "
                    "exists for this does not open"))
                continue
            with door.session_transaction() as sess:
                if not sess.get("demo"):
                    findings.append(Finding(
                        f"POST /demo/{role}",
                        "signed in without marking the session as a demo, so no page "
                        "will warn that this is real data"))
            landed = door.get(landing, follow_redirects=True)
            if landed.status_code != 200:
                findings.append(Finding(
                    f"POST /demo/{role}",
                    f"did not reach {landing} — it returned {landed.status_code}"))
            elif "demobar" not in landed.get_data(as_text=True):
                findings.append(Finding(
                    landing,
                    "a demo session renders with no banner. Someone can spend an "
                    "afternoon in here without being told the data is real"))

        on_home = ctx.app.test_client().get("/", follow_redirects=True).get_data(as_text=True)
        if "demo-doors" not in on_home:
            findings.append(Finding(
                "GET /", "DEMO_MODE is on and the home page offers no way in"))
    finally:
        _with_demo(ctx, was)
    return findings


def prove(ctx):
    """Three defects: the check moves to the view, it leaks, and it goes quiet."""
    from pathlib import Path

    caught = []
    auth_src = Path(__file__).resolve().parents[2] / "monti" / "auth.py"
    home_src = (Path(__file__).resolve().parents[2] / "monti" / "templates"
                / "public" / "home.html")
    bar_src = (Path(__file__).resolve().parents[2] / "monti" / "templates"
               / "_demobar.html")

    def attempt(label, path, before, after, matches):
        original = path.read_text()
        broken = original.replace(before, after, 1)
        assert broken != original, f"proof {label!r} no longer matches the source"
        path.write_text(broken)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            path.write_text(original)
            ctx.reload()

    # 1. The guard leaves the route. This is the one that matters: the button
    #    disappears from the page and the door stays open behind it.
    attempt("the route stopped checking the flag", auth_src,
            '    if not current_app.config["DEMO_MODE"]:\n        abort(404)',
            '    if False:\n        abort(404)',
            lambda f: "has to be absent" in f.detail)

    # 2. The panel renders regardless, so the credentials are published.
    attempt("the demo panel rendered with the flag off", home_src,
            "    {% if cfg.DEMO_MODE %}", "    {% if True %}",
            lambda f: "still points at a demo route" in f.detail
            or "panel renders with DEMO_MODE off" in f.detail)

    # 3. The session is a demo and nothing says so.
    attempt("the demo banner stopped rendering", bar_src,
            "{% if session.get('demo') and cfg.DEMO_MODE %}", "{% if False %}",
            lambda f: "renders with no banner" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A43", "The passwordless demo doors do not exist unless enabled",
                run, prove)]
