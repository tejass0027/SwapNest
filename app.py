import os

from flask import Flask, g, session, render_template

import db
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Upload limits and directory. 4 MB per request is enough for any
    # reasonable listing image; anything larger triggers a 413.
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(
        app.static_folder, "img", "uploads"
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    import auth
    app.register_blueprint(auth.bp)

    import listings
    app.register_blueprint(listings.bp)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
        else:
            g.user = db.get_db().execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()

    @app.context_processor
    def inject_globals():
        return {
            "site_name": app.config["SITE_NAME"],
            "demo_mode": app.config["DEMO_MODE"],
            "social_accounts_enabled": app.config["ENABLE_SOCIAL_ACCOUNTS"],
            "current_user": g.get("user"),
        }

    @app.template_filter("usd")
    def usd_filter(cents):
        return f"{cents / 100:,.2f}"

    return app


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    create_app().run(debug=True, port=port)
