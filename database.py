import sqlite3
import secrets
import string
from datetime import datetime, timedelta

from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT NOT NULL,
            banned INTEGER DEFAULT 0,
            role_mode TEXT DEFAULT 'user'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            activated_at TEXT NOT NULL,
            UNIQUE(license_id, user_id)
        )
    """)

    conn.commit()
    conn.close()


def register_user(user):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.utcnow().isoformat()
    ))

    cur.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (
        user.username or "",
        user.first_name or "",
        user.id
    ))

    conn.commit()
    conn.close()


def is_banned(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT banned FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    return bool(row["banned"]) if row else False


def set_banned(user_id, value):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET banned = ? WHERE user_id = ?",
        (1 if value else 0, user_id)
    )
    conn.commit()
    conn.close()


def set_mode(user_id, mode):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET role_mode = ? WHERE user_id = ?",
        (mode, user_id)
    )
    conn.commit()
    conn.close()


def get_mode(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT role_mode FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    return row["role_mode"] if row else "user"


def generate_license(minutes=None):
    alphabet = string.ascii_uppercase + string.digits

    while True:
        key = "NUTHH-" + "-".join(
            "".join(secrets.choice(alphabet) for _ in range(4))
            for _ in range(3)
        )

        conn = get_connection()
        exists = conn.execute(
            "SELECT id FROM licenses WHERE key = ?",
            (key,)
        ).fetchone()

        if not exists:
            break

        conn.close()

    now = datetime.utcnow()

    if minutes is None:
        expires_at = None
    else:
        expires_at = (now + timedelta(minutes=minutes)).isoformat()

    conn.execute("""
        INSERT INTO licenses
        (key, created_at, expires_at, active)
        VALUES (?, ?, ?, 1)
    """, (
        key,
        now.isoformat(),
        expires_at
    ))

    conn.commit()
    conn.close()

    return key, expires_at


def get_license(key):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM licenses
        WHERE key = ?
    """, (key.strip().upper(),)).fetchone()

    conn.close()

    return row


def activate_license(key, user_id):
    key = key.strip().upper()

    conn = get_connection()

    license_row = conn.execute("""
        SELECT *
        FROM licenses
        WHERE key = ?
    """, (key,)).fetchone()

    if not license_row:
        conn.close()
        return False, "❌ Invalid license key."

    if not license_row["active"]:
        conn.close()
        return False, "⛔ This license key is disabled."

    if license_row["expires_at"]:
        expires = datetime.fromisoformat(license_row["expires_at"])

        if datetime.utcnow() >= expires:
            conn.close()
            return False, "⏰ This license key has expired."

    try:
        conn.execute("""
            INSERT OR IGNORE INTO activations
            (license_id, user_id, activated_at)
            VALUES (?, ?, ?)
        """, (
            license_row["id"],
            user_id,
            datetime.utcnow().isoformat()
        ))

        conn.commit()

    finally:
        conn.close()

    return True, "✅ License activated successfully."


def user_has_valid_license(user_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT l.*
        FROM licenses l
        INNER JOIN activations a
        ON l.id = a.license_id
        WHERE a.user_id = ?
        AND l.active = 1
    """, (user_id,)).fetchall()

    conn.close()

    now = datetime.utcnow()

    for row in rows:
        if row["expires_at"] is None:
            return True

        if now < datetime.fromisoformat(row["expires_at"]):
            return True

    return False


def list_licenses():
    conn = get_connection()
    rows = conn.execute("""
        SELECT *
        FROM licenses
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return rows


def disable_license(key):
    conn = get_connection()
    cur = conn.execute(
        "UPDATE licenses SET active = 0 WHERE key = ?",
        (key.strip().upper(),)
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()

    return changed > 0


def enable_license(key):
    conn = get_connection()
    cur = conn.execute(
        "UPDATE licenses SET active = 1 WHERE key = ?",
        (key.strip().upper(),)
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()

    return changed > 0


def delete_license(key):
    conn = get_connection()

    row = conn.execute(
        "SELECT id FROM licenses WHERE key = ?",
        (key.strip().upper(),)
    ).fetchone()

    if not row:
        conn.close()
        return False

    conn.execute(
        "DELETE FROM activations WHERE license_id = ?",
        (row["id"],)
    )

    conn.execute(
        "DELETE FROM licenses WHERE id = ?",
        (row["id"],)
    )

    conn.commit()
    conn.close()

    return True


def extend_license(key, minutes):
    conn = get_connection()

    row = conn.execute("""
        SELECT expires_at
        FROM licenses
        WHERE key = ?
    """, (key.strip().upper(),)).fetchone()

    if not row:
        conn.close()
        return False

    if row["expires_at"] is None:
        conn.close()
        return True

    current = datetime.fromisoformat(row["expires_at"])

    if current < datetime.utcnow():
        current = datetime.utcnow()

    new_expiry = current + timedelta(minutes=minutes)

    conn.execute("""
        UPDATE licenses
        SET expires_at = ?, active = 1
        WHERE key = ?
    """, (
        new_expiry.isoformat(),
        key.strip().upper()
    ))

    conn.commit()
    conn.close()

    return True


def count_users():
    conn = get_connection()
    value = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]
    conn.close()
    return value


def count_licenses():
    conn = get_connection()
    value = conn.execute(
        "SELECT COUNT(*) FROM licenses"
    ).fetchone()[0]
    conn.close()
    return value


def count_active_licenses():
    conn = get_connection()
    value = conn.execute(
        "SELECT COUNT(*) FROM licenses WHERE active = 1"
    ).fetchone()[0]
    conn.close()
    return value


def count_activations():
    conn = get_connection()
    value = conn.execute(
        "SELECT COUNT(*) FROM activations"
    ).fetchone()[0]
    conn.close()
    return value
