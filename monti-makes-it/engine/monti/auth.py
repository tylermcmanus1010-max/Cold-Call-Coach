"""Authentication, roles, and hard client isolation.

Two roles only:
  ADMIN  — full access to the admin bay, sees every customer.
  CLIENT — bound to exactly one customer_id; can only ever read rows
           belonging to that customer. Enforced in `own_or_404`.
"""
import functools
import hmac
import secrets

from flask import (
    Blueprint, abort, current_app, flash, g, redirect,
    render_template, request, session, url_for,
)
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

from .db import execute, query
from .utils import now_str

bp = Blueprint("auth", __name__)


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------
CSRF_EXEMPT_BLUEPRINTS = {"webhooks"}


def csrf_token() -> str:
    """Per-session CSRF token, minted on first use."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def csrf_input() -> Markup:
    return Markup(f'<input type="hidden" name="_csrf" value="{csrf_token()}">')


def check_csrf():
    """Reject any state-changing request without a matching token.

    Webhooks are exempt — they are authenticated by their provider signature,
    not by a browser session.
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    if request.blueprint in CSRF_EXEMPT_BLUEPRINTS:
        return None
    sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get("_csrf") or ""
    if not expected or not hmac.compare_digest(sent, expected):
        current_app.logger.warning("CSRF check failed on %s", request.path)
        abort(400)
    return None


# --------------------------------------------------------------------------
# session plumbing
# --------------------------------------------------------------------------
def load_logged_in_user():
    uid = session.get("user_id")
    g.user = None
    g.customer = None
    g.viewing_as = False
    if uid is None:
        return
    g.user = query("SELECT * FROM users WHERE id = ? AND is_active = 1", (uid,), one=True)
    if g.user is None:
        session.clear()
        return
    if g.user["customer_id"]:
        g.customer = query("SELECT * FROM customers WHERE id = ?", (g.user["customer_id"],), one=True)
    elif g.user["role"] == "ADMIN" and session.get("view_as"):
        # An admin opening a client's portal from the admin portal. Read-through
        # only — every write still records the admin as the actor.
        g.customer = query("SELECT * FROM customers WHERE id = ?", (session["view_as"],), one=True)
        g.viewing_as = g.customer is not None


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.get("user") is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.get("user") is None:
            return redirect(url_for("auth.login", next=request.full_path))
        if g.user["role"] != "ADMIN":
            abort(403)
        return view(**kwargs)
    return wrapped


def client_required(view):
    """A member's own portal — or an admin who has opened it from the admin portal."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.get("user") is None:
            return redirect(url_for("auth.login", next=request.full_path))
        if g.user["role"] == "CLIENT" and g.user["customer_id"]:
            return view(**kwargs)
        if g.user["role"] == "ADMIN" and g.get("viewing_as"):
            return view(**kwargs)
        abort(403)
    return wrapped


def own_or_404(row):
    """The isolation gate. A CLIENT may only ever touch its own customer's rows.

    Every portal query passes its result through here, so a guessed id in the
    URL returns 404 rather than another client's data.
    """
    if row is None:
        abort(404)
    if g.get("user") and g.user["role"] == "ADMIN":
        return row
    customer_id = g.user["customer_id"] if g.get("user") else None
    row_customer = row["customer_id"] if "customer_id" in row.keys() else None
    if customer_id is None or row_customer != customer_id:
        abort(404)
    return row


# --------------------------------------------------------------------------
# user management
# --------------------------------------------------------------------------
def create_user(email, password, name=None, role="CLIENT", customer_id=None,
                must_change_password=False):
    return execute(
        "INSERT INTO users (email, password_hash, name, role, customer_id, must_change_password) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (email.strip().lower(), generate_password_hash(password), name, role,
         customer_id, 1 if must_change_password else 0),
    )


def generate_password(length: int = 12) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_portal_user(customer_row, name=None):
    """Idempotently give a customer a portal login. Returns (user_id, plain_password|None)."""
    existing = query(
        "SELECT * FROM users WHERE customer_id = ? ORDER BY id LIMIT 1",
        (customer_row["id"],), one=True,
    )
    if existing:
        return existing["id"], None
    pw = generate_password()
    uid = create_user(
        email=customer_row["email"],
        password=pw,
        name=name or customer_row["contact_name"] or customer_row["company_name"],
        role="CLIENT",
        customer_id=customer_row["id"],
        must_change_password=True,
    )
    return uid, pw


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------
@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.get("user"):
        return redirect(url_for("admin.dashboard") if g.user["role"] == "ADMIN"
                        else url_for("portal.dashboard"))
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Those credentials don't match an account."
        elif not user["is_active"]:
            error = "This account has been deactivated. Contact your account manager."
        if error is None:
            # `session.clear()` is right — a fresh session on sign-in is what
            # stops a fixated session id from surviving the login. But the
            # language someone chose is not credentials, and clearing it meant a
            # member picked Español, signed in, and landed in English.
            locale = session.get("locale")
            session.clear()
            if locale:
                session["locale"] = locale
            session["user_id"] = user["id"]
            session.permanent = True
            execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_str(), user["id"]))
            nxt = request.args.get("next") or request.form.get("next")
            if nxt and nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard") if user["role"] == "ADMIN"
                            else url_for("portal.dashboard"))
        flash(error, "error")
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.route("/demo/<role>", methods=("POST",))
def demo(role):
    """Sign in as the demo member or the demo admin, without a password.

    Only when DEMO_MODE is set. Off — which is the default and what production
    gets — this route does not answer at all: a 404, not a 403, because the
    existence of a passwordless door is itself information.

    There is no separate demo dataset. The member door lands in Boars Head's
    real portal and the admin door reaches every account, which is exactly what
    makes this dangerous and exactly what makes it useful for reviewing. The
    banner it turns on says so on every page, so nobody is halfway through a
    session wondering whether what they are looking at is real.
    """
    if not current_app.config["DEMO_MODE"]:
        abort(404)

    if role == "admin":
        user = query("SELECT * FROM users WHERE role = 'ADMIN' AND is_active = 1 "
                     "ORDER BY id LIMIT 1", one=True)
        landing = "admin.dashboard"
    elif role == "member":
        user = query(
            "SELECT u.* FROM users u JOIN customers c ON c.id = u.customer_id "
            "WHERE u.role = 'CLIENT' AND u.is_active = 1 AND c.is_fixture = 0 "
            "ORDER BY u.id LIMIT 1", one=True)
        landing = "portal.dashboard"
    else:
        abort(404)

    if user is None:
        flash("There is no account to demo yet. Run `flask launch` first.", "error")
        return redirect(url_for("public.home"))

    locale = session.get("locale")
    session.clear()
    if locale:
        session["locale"] = locale
    session["user_id"] = user["id"]
    session["demo"] = True          # what the banner reads
    session.permanent = True
    current_app.logger.warning("Demo sign-in as %s (%s) — DEMO_MODE is on",
                               user["email"], user["role"])
    return redirect(url_for(landing))


@bp.route("/logout")
def logout():
    # Same on the way out: signing out should not also change the language of
    # the page they land on.
    locale = session.get("locale")
    session.clear()
    if locale:
        session["locale"] = locale
    flash("Signed out.", "ok")
    return redirect(url_for("public.home"))


@bp.route("/account/password", methods=("GET", "POST"))
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        confirm = request.form.get("confirm_password") or ""
        if not check_password_hash(g.user["password_hash"], current):
            flash("Current password is incorrect.", "error")
        elif len(new) < 8:
            flash("Use at least 8 characters.", "error")
        elif new != confirm:
            flash("The two new passwords don't match.", "error")
        else:
            execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                (generate_password_hash(new), g.user["id"]),
            )
            flash("Password updated.", "ok")
            return redirect(url_for("portal.dashboard") if g.user["role"] == "CLIENT"
                            else url_for("admin.dashboard"))
    return render_template("auth/change_password.html")


def init_app(app):
    app.before_request(load_logged_in_user)
    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["csrf_input"] = csrf_input
