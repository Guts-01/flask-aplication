

import hmac
import hashlib
import secrets

from flask import abort, flash, redirect, request, session, url_for
from flask_login import current_user, logout_user


def install_security(app):
    @app.context_processor
    def csrf_context():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]

        return {"csrf_token": csrf_token}

    @app.before_request
    def verify_csrf():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            expected = session.get("csrf_token", "")
            received = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected, received):
                abort(400, description="Formulário inválido. Atualize a página e tente novamente.")

    @app.before_request
    def verify_session_password():
        if current_user.is_authenticated:
            expected = hashlib.sha256(current_user.password.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(session.get("auth_hash", ""), expected):
                logout_user()
                session.clear()
                flash("Sua sessão expirou. Entre novamente.", "info")
                return redirect(url_for("auth.login"))

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; form-action 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'"
        )
        return response
