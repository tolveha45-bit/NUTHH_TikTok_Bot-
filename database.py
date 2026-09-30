import sqlite3
import secrets
import string
from datetime import datetime, timedelta

from config import DATABASE_PATH


def connect():
    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            mode TEXT DEFAULT 'user',
            blocked INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            expires_at TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            user_id INTEGER,
            activated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def register_user(user):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (
            user_id,
            username,
            first_name,
            mode,
            blocked,
            downloads,
            created_at
        )
        VALUES (?, ?, ?, 'user', 0, 0, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.now().isoformat()
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


def get_user(user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    conn.close()

    return row


def set_mode(user_id, mode):
    conn = connect()

    conn.execute("""
        UPDATE users
        SET mode = ?
        WHERE user_id = ?
    """, (mode, user_id))

    conn.commit()
    conn.close()


def get_mode(user_id):
    row = get_user(user_id)

    if not row:
        return "user"

    return row["mode"]


def set_blocked(user_id, blocked):
    conn = connect()

    conn.execute("""
        UPDATE users
        SET blocked = ?
        WHERE user_id = ?
    """, (1 if blocked else 0, user_id))

    conn.commit()
    conn.close()


def is_blocked(user_id):
    row = get_user(user_id)

    if not row:
        return False

    return bool(row["blocked"])


def increment_download(user_id):
    conn = connect()

    conn.execute("""
        UPDATE users
        SET downloads = downloads + 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()


def total_users():
    conn = connect()

    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")

    result = cur.fetchone()[0]

    conn.close()

    return result


def total_downloads():
    conn = connect()

    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(downloads), 0)
        FROM users
    """)

    result = cur.fetchone()[0]

    conn.close()

    return result


def generate_key(minutes=None):
    alphabet = string.ascii_uppercase + string.digits

    key = (
        "NUTHH-"
        + "".join(secrets.choice(alphabet) for _ in range(5))
        + "-"
        + "".join(secrets.choice(alphabet) for _ in range(5))
        + "-"
        + "".join(secrets.choice(alphabet) for _ in range(5))
    )

    if minutes is None:
        expires_at = None
    else:
        expires_at = (
            datetime.now() + timedelta(minutes=minutes)
        ).isoformat()

    conn = connect()

    conn.execute("""
        INSERT INTO licenses
        (
            license_key,
            expires_at,
            enabled,
            created_at
        )
        VALUES (?, ?, 1, ?)
    """, (
        key,
        expires_at,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return key


def activate_license(user_id, key):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM licenses
        WHERE license_key = ?
    """, (key.strip().upper(),))

    license_row = cur.fetchone()

    if not license_row:
        conn.close()
        return False, "❌ License key not found."

    if not license_row["enabled"]:
        conn.close()
        return False, "❌ This license is disabled."

    expires_at = license_row["expires_at"]

    if expires_at:
        expiry = datetime.fromisoformat(expires_at)

        if expiry <= datetime.now():
            conn.close()
            return False, "⏰ This license has expired."

    cur.execute("""
        INSERT INTO activations
        (
            license_key,
            user_id,
            activated_at
        )
        VALUES (?, ?, ?)
    """, (
        key.strip().upper(),
        user_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return True, "✅ License activated successfully."


def has_valid_license(user_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT l.*
        FROM licenses l
        INNER JOIN activations a
        ON l.license_key = a.license_key
        WHERE a.user_id = ?
        AND l.enabled = 1
        ORDER BY a.id DESC
    """, (user_id,))

    rows = cur.fetchall()

    conn.close()

    now = datetime.now()

    for row in rows:

        if row["expires_at"] is None:
            return True

        if datetime.fromisoformat(row["expires_at"]) > now:
            return True

    return False


def list_licenses():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM licenses
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return rows


def set_license_enabled(key, enabled):
    conn = connect()

    conn.execute("""
        UPDATE licenses
        SET enabled = ?
        WHERE license_key = ?
    """, (
        1 if enabled else 0,
        key.strip().upper()
    ))

    conn.commit()
    conn.close()


def delete_license(key):
    conn = connect()

    conn.execute("""
        DELETE FROM licenses
        WHERE license_key = ?
    """, (key.strip().upper(),))

    conn.execute("""
        DELETE FROM activations
        WHERE license_key = ?
    """, (key.strip().upper(),))

    conn.commit()
    conn.close()


def extend_license(key, minutes):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT expires_at
        FROM licenses
        WHERE license_key = ?
    """, (key.strip().upper(),))

    row = cur.fetchone()

    if not row:
        conn.close()
        return False

    if row["expires_at"] is None:
        conn.close()
        return True

    current_expiry = datetime.fromisoformat(row["expires_at"])

    if current_expiry < datetime.now():
        current_expiry = datetime.now()

    new_expiry = current_expiry + timedelta(minutes=minutes)

    cur.execute("""
        UPDATE licenses
        SET expires_at = ?
        WHERE license_key = ?
    """, (
        new_expiry.isoformat(),
        key.strip().upper()
    ))

    conn.commit()
    conn.close()

    return True
