"""Fábrica da aplicação e configuração dos componentes."""

import os
from pathlib import Path

import click
from flask import Flask
from sqlalchemy import func

from .extensions import bcrypt, db, login_manager
from .security import install_security


def _local_secret(instance_path: str) -> str:
    """Mantém as sessões válidas entre reinicializações sem chave fixa no código."""
    key_file = Path(instance_path) / "secret_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        try:
            with key_file.open("x", encoding="ascii") as file:
                file.write(os.urandom(32).hex())
        except FileExistsError:
            pass
    return key_file.read_text(encoding="ascii").strip()


def create_app(test_config=None):
    # Usa a pasta instance original, fora do pacote, para preservar o SQLite.
    instance_path = Path(__file__).resolve().parent.parent / "instance"
    app = Flask(__name__, instance_path=str(instance_path), instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or _local_secret(app.instance_path),
        SQLALCHEMY_DATABASE_URI="sqlite:///db.sqlite",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre na sua conta para continuar."
    login_manager.login_message_category = "info"
    install_security(app)

    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    from .models import User

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    with app.app_context():
        db.create_all()
        # A versão antiga criava automaticamente um administrador com senha "222".
        # Desativa somente contas administrativas que ainda usam essa senha.
        weak_admins = User.query.filter_by(is_admin=True).all()
        for user in weak_admins:
            if bcrypt.check_password_hash(user.password, "222"):
                user.password = bcrypt.generate_password_hash(os.urandom(32).hex()).decode("utf-8")
                user.is_admin = False
        if db.session.dirty:
            db.session.commit()

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nome")
    @click.option("--email", prompt="Email")
    @click.password_option(confirmation_prompt=True)
    def create_admin(name, email, password):
        """Cria ou atualiza um administrador com uma senha própria."""
        from .validation import normalize_email, validate_account

        name = name.strip()
        email = normalize_email(email)
        error = validate_account(name, email, password)
        if error:
            raise click.ClickException(error)
        user = User.query.filter(func.lower(User.email) == email).first()
        if user is None:
            user = User(name=name, email=email)
            db.session.add(user)
        else:
            user.name = name
        user.password = bcrypt.generate_password_hash(password).decode("utf-8")
        user.is_admin = True
        db.session.commit()
        click.echo("Administrador configurado.")

    return app
