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
        """Load demo data (customers, quotes, catalog, orders)."""
        from .seed import run_seed
        run_seed()

    return app
