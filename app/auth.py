"""
Жүйеге кіру: құпиясөзді хэштеу және тексеру.

Құпиясөз базада ашық мәтін түрінде сақталмайды. hashlib модулінің
PBKDF2-HMAC-SHA256 алгоритмі кездейсоқ «тұз» (salt) қосып хэш есептейді.
"""
import hashlib
import hmac
import secrets

ITERATIONS = 200_000
ROLE_NAMES = {"admin": "әкімші", "visitor": "қонақ"}


def hash_password(password):
    """Құпиясөздің хэші: 'pbkdf2_sha256$итерация$тұз$хэш' пішімінде."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password, stored):
    """Енгізілген құпиясөздің хэшін қайта есептеп, сақталған хэшпен салыстырады."""
    try:
        _, iterations, salt, expected = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def authenticate(conn, username, password):
    """Логин мен құпиясөз дұрыс болса пайдаланушыны, әйтпесе None қайтарады."""
    row = conn.execute(
        "SELECT id, username, password_hash, role, full_name FROM users WHERE username = ?",
        ((username or "").strip(),)).fetchone()
    if row is None or not verify_password(password or "", row[2]):
        return None
    return {"id": row[0], "username": row[1], "role": row[3], "full_name": row[4]}
