import re
import tempfile
import unittest
from pathlib import Path

from training_app import create_app
from training_app.extensions import bcrypt, db
from training_app.models import User


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "test.sqlite"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key-only",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def token(self, path):
        page = self.client.get(path)
        self.assertEqual(page.status_code, 200)
        match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def register(self, email="ana@example.com"):
        return self.client.post("/register", data={
            "csrf_token": self.token("/register"),
            "name": "Ana",
            "email": email,
            "password": "senha-segura-123",
            "confirm_password": "senha-segura-123",
        })

    def login(self, email="ana@example.com", password="senha-segura-123"):
        return self.client.post("/login", data={
            "csrf_token": self.token("/login"),
            "email": email,
            "password": password,
        })

    def test_registration_login_logout_and_csrf(self):
        self.assertEqual(self.client.post("/register", data={"name": "Ana"}).status_code, 400)
        self.assertEqual(self.register().status_code, 302)
        self.assertIn(b"cadastrado", self.register().data)
        self.assertEqual(self.login().status_code, 302)
        self.assertIn("Ana", self.client.get("/").get_data(as_text=True))
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout").status_code, 400)
        self.assertEqual(self.client.post("/logout", data={"csrf_token": self.token("/profile")}).status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_password_change_requires_current_password(self):
        self.register()
        self.login()
        token = self.token("/profile")
        response = self.client.post("/change_password", data={
            "csrf_token": token,
            "old_password": "errada",
            "new_password": "outra-senha-segura-123",
            "confirm_password": "outra-senha-segura-123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.post("/change_password", data={
            "csrf_token": token,
            "old_password": "senha-segura-123",
            "new_password": "outra-senha-segura-123",
            "confirm_password": "outra-senha-segura-123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.login(password="outra-senha-segura-123").status_code, 302)

    def test_existing_mixed_case_email_still_works(self):
        with self.app.app_context():
            db.session.add(User(
                name="Ana",
                email="Ana@Example.com",
                password=bcrypt.generate_password_hash("senha-segura-123").decode(),
            ))
            db.session.commit()
        self.assertEqual(self.login(email="ana@example.com").status_code, 302)
        token = self.token("/profile")
        self.client.post("/logout", data={"csrf_token": token})
        self.assertIn(b"cadastrado", self.register(email="ana@example.com").data)

    def test_admin_access_and_delete(self):
        self.register()
        self.login()
        self.assertEqual(self.client.get("/admin/").status_code, 403)
        with self.app.app_context():
            user = User.query.filter_by(email="ana@example.com").one()
            user.is_admin = True
            other = User(name="Bia", email="bia@example.com", password=bcrypt.generate_password_hash("senha-segura-456").decode())
            db.session.add(other)
            db.session.commit()
            other_id = other.id
            own_id = user.id
        token = self.token("/profile")
        self.client.post("/logout", data={"csrf_token": token})
        self.login()
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        token = self.token("/admin/")
        self.assertEqual(self.client.post(f"/admin/users/{own_id}/delete", data={"csrf_token": token}).status_code, 302)
        self.assertEqual(self.client.post(f"/admin/users/{other_id}/delete", data={"csrf_token": token}).status_code, 302)
        with self.app.app_context():
            self.assertIsNone(db.session.get(User, other_id))
            self.assertIsNotNone(db.session.get(User, own_id))

    def test_legacy_admin_is_disabled_and_password_reset_expires_session(self):
        with self.app.app_context():
            db.session.add(User(
                name="Admin antigo",
                email="admin@example.com",
                password=bcrypt.generate_password_hash("222").decode(),
                is_admin=True,
            ))
            db.session.commit()
        restarted = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key-only",
            "SQLALCHEMY_DATABASE_URI": self.app.config["SQLALCHEMY_DATABASE_URI"],
        })
        with restarted.app_context():
            admin = User.query.filter_by(email="admin@example.com").one()
            self.assertFalse(admin.is_admin)
            self.assertFalse(bcrypt.check_password_hash(admin.password, "222"))
            db.session.remove()
            db.engine.dispose()

        self.register()
        self.login()
        with self.app.app_context():
            user = User.query.filter_by(email="ana@example.com").one()
            user.password = bcrypt.generate_password_hash("senha-renovada-123").decode()
            db.session.commit()
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)


if __name__ == "__main__":
    unittest.main()
