"""Monti Makes It — application factory."""
import os
from pathlib import Path

from flask import Flask, g, render_template

from .config import Config


def load_dotenv(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_app(config_object=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from . import db, auth
    db.init_app(app)
    auth.init_app(app)

    from .blueprints import public, portal, admin, webhooks
    app.register_blueprint(auth.bp)
    app.register_blueprint(public.bp)
    app.register_blueprint(portal.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(webhooks.bp)

    from . import utils
    app.jinja_env.filters["money"] = utils.money
    app.jinja_env.filters["dt"] = utils.pretty_dt
    app.jinja_env.filters["date"] = lambda v: utils.pretty_dt(v, with_time=False)
    app.jinja_env.filters["relative"] = utils.relative
    app.jinja_env.filters["initials"] = utils.initials

    @app.context_processor
    def inject_globals():
        return {
            "cfg": app.config,
            "company": app.config["COMPANY_NAME"],
            "status_label": utils.status_label,
            "countdown": utils.countdown,
            "now": utils.utcnow(),
        }

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.cli.command("seed")
    def seed_command():
        """Load demo data (customers, quotes, catalogue, orders). Never in production."""
        from .seed import run_seed
        run_seed()

    @app.cli.command("purge-fixtures")
    def purge_command():
        """Delete every seeded row, after a verified backup. Prints the evidence."""
        import json
        from . import purge as purge_mod
        from .db import init_db
        init_db()
        result = purge_mod.purge()
        print(json.dumps({k: v for k, v in result.items() if k != "inventory"}, indent=2))
        print(f"inventory: {len(result['inventory'])} fixture rows deleted")

    @app.cli.command("launch")
    def launch_command():
        """Bring the database to its launch state: no fixtures, Boars Head live."""
        from . import launch as launch_mod
        from .agents import provision_agent, unprovisioned_customers
        from .auth import create_user, generate_password
        from .db import init_db, query
        init_db()

        if query("SELECT COUNT(*) AS c FROM customers WHERE is_fixture = 1", one=True)["c"]:
            raise SystemExit(
                "Fixture rows are still present. Run `flask purge-fixtures` first — "
                "launching on top of demo data is how a demo customer reaches production.")

        if not query("SELECT id FROM users WHERE role = 'ADMIN'", one=True):
            pw = generate_password()
            create_user("admin@montimakesit.com", pw, name="Admin", role="ADMIN",
                        must_change_password=True)
            print(f"  admin@montimakesit.com / {pw}  (must change on first sign-in)")

        launch_mod.provision_freight_lanes()
        customer_id = launch_mod.provision_boars_head()
        # The zero-orphan rule: no customer without an agent, including any that
        # predate this command.
        for row in unprovisioned_customers():
            provision_agent(row["id"])
        print(f"Boars Head is live as customer #{customer_id}.")

    return app
