"""I build CourseShelf here. Developed by Herve Friend KUBANA.

I refuse to boot with debug on when I set APP_ENV=production.
I sign my session cookies with SECRET_KEY, so I use the same secret on Web01 and Web02.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, session
from werkzeug.exceptions import RequestEntityTooLarge

from app.core import format_date

ROOT = Path(__file__).resolve().parents[1]


def load_environment():
    """I load my .env, and I leave a value alone when I already set it in the shell."""
    load_dotenv(ROOT / ".env", override=False)


def create_app():
    load_environment()
    _reject_unsafe_production_settings()

    app = Flask(
        __name__,
        template_folder=str(ROOT / "app" / "templates"),
        static_folder=str(ROOT / "app" / "static"),
    )
    secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret or secret.startswith("replace-with"):
        raise RuntimeError("Set SECRET_KEY in the environment before starting CourseShelf.")

    app.config.update(
        SECRET_KEY=secret,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        MAX_CONTENT_LENGTH=64 * 1024,
        DEBUG=os.environ.get("FLASK_DEBUG", "0") == "1",
        BACKEND_NAME=os.environ.get("BACKEND_NAME", "local"),
    )

    @app.template_filter("shortdate")
    def shortdate(value):
        return format_date(value)

    @app.before_request
    def protect_post_forms():
        if request.method != "POST":
            return None
        from app.core import csrf_tokens_match

        sent = request.form.get("csrf_token", "")
        if not csrf_tokens_match(sent, session.get("csrf_token", "")):
            return (
                render_error(
                    "The form expired",
                    "Reload the page and submit the form again. The protection token did not match this session.",
                ),
                400,
            )
        return None

    @app.after_request
    def add_response_headers(response):
        response.headers["X-CourseShelf-Backend"] = app.config["BACKEND_NAME"]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        # Open Library redirects some covers to archive.org. I allow those image hosts.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' https://covers.openlibrary.org https://archive.org https://*.archive.org https://*.us.archive.org; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_error(
                "That page is not on the shelf",
                "Use Course shelf, Offer a book, or My loans.",
            ),
            404,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return (
            render_error(
                "That submission is too large",
                "Shorten the note and try again.",
            ),
            413,
        )

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("unhandled error")
        return (
            render_error(
                "The shelf hit a problem",
                "The details were written to the server log. Try the page again in a moment.",
            ),
            500,
        )

    from app.routes import register_routes

    register_routes(app)
    app.logger.info(
        "CourseShelf ready backend=%s debug=%s",
        app.config["BACKEND_NAME"],
        app.debug,
    )
    return app


def render_error(heading, detail):
    from flask import render_template

    return render_template("error.html", heading=heading, detail=detail)


def _reject_unsafe_production_settings():
    if os.environ.get("APP_ENV") != "production":
        return
    if os.environ.get("FLASK_DEBUG", "0") == "1":
        raise RuntimeError("Refusing to start with FLASK_DEBUG enabled when APP_ENV=production.")
    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32 or secret.startswith("replace-with"):
        raise RuntimeError("Production requires a SECRET_KEY of at least 32 characters.")
