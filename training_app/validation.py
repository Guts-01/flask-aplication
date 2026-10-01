import re


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(email):
    return (email or "").strip().lower()


def validate_password(password):
    if not password or len(password) < 12:
        return "Use uma senha com pelo menos 12 caracteres."
    if len(password.encode("utf-8")) > 72:
        return "A senha deve ter no máximo 72 bytes."
    return None


def validate_account(name, email, password):
    if not name or len(name) > 150:
        return "Informe um nome com até 150 caracteres."
    if len(email) > 150 or not EMAIL_PATTERN.fullmatch(email):
        return "Informe um email válido com até 150 caracteres."
    return validate_password(password)
