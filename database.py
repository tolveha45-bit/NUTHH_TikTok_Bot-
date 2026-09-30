import sqlite3
import secrets
import string

from datetime import datetime, timedelta

from config import DATABASE_PATH


def connect():
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
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
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            mode TEXT DEFAULT 'user',
            blocked INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            expires_at TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            activated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USERS
# =========================================================

def register_user(user):

    conn = connect()

    conn.execute("""
        INSERT INTO users (
            user_id,
            username,
            first_name,
            mode,
            blocked,
            downloads,
            created_at
        )
        VALUES (?, ?, ?, 'user', 0, 0, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_user(user_id):

    conn = connect()

    cur = conn.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    conn.close()

    return row


def set_mode(user_id, mode):

    conn = connect()

    conn.execute("""
        UPDATE users
        SET mode = ?
        WHERE user_id = ?
    """, (
        mode,
        user_id
    ))

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
    """, (
        1 if blocked else 0,
        user_id
    ))

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

    cur = conn.execute("""
        SELECT COUNT(*)
        FROM users
    """)

    value = cur.fetchone()[0]

    conn.close()

    return value


def total_downloads():

    conn = connect()

    cur = conn.execute("""
        SELECT COALESCE(SUM(downloads), 0)
        FROM users
    """)

    value = cur.fetchone()[0]

    conn.close()

    return value


def all_users():

    conn = connect()

    cur = conn.execute("""
        SELECT *
        FROM users
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return rows


# =========================================================
# LICENSE
# =========================================================

def generate_license(minutes=None):

    alphabet = string.ascii_uppercase + string.digits

    while True:

        key = (
            "NUTHH-"
            + "".join(
                secrets.choice(alphabet)
                for _ in range(5)
            )
            + "-"
            + "".join(
                secrets.choice(alphabet)
                for _ in range(5)
            )
            + "-"
            + "".join(
                secrets.choice(alphabet)
                for _ in range(5)
            )
        )

        conn = connect()

        cur = conn.execute("""
            SELECT id
            FROM licenses
            WHERE license_key = ?
        """, (key,))

        exists = cur.fetchone()

        conn.close()

        if not exists:
            break

    if minutes is None:

        expires_at = None

    else:

        expires_at = (
            datetime.now()
            + timedelta(minutes=minutes)
        ).isoformat()

    conn = connect()

    conn.execute("""
        INSERT INTO licenses (
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


def get_license(key):

    conn = connect()

    cur = conn.execute("""
        SELECT *
        FROM licenses
        WHERE license_key = ?
    """, (
        key.strip().upper(),
    ))

    row = cur.fetchone()

    conn.close()

    return row


def activate_license(user_id, key):

    key = key.strip().upper()

    row = get_license(key)

    if not row:
        return False, "❌ License key not found."

    if not row["enabled"]:
        return False, "🔴 This license is disabled."

    if row["expires_at"]:

        expiry = datetime.fromisoformat(
            row["expires_at"]
        )

        if expiry <= datetime.now():

            return False, "⏰ This license has expired."

    conn = connect()

    conn.execute("""
        INSERT INTO activations (
            license_key,
            user_id,
            activated_at
        )
        VALUES (?, ?, ?)
    """, (
        key,
        user_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return True, "✅ License activated successfully."


def has_valid_license(user_id):

    conn = connect()

    cur = conn.execute("""
        SELECT l.*
        FROM licenses l
        INNER JOIN activations a
            ON a.license_key = l.license_key
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

        expiry = datetime.fromisoformat(
            row["expires_at"]
        )

        if expiry > now:
            return True

    return False


def list_licenses():

    conn = connect()

    cur = conn.execute("""
        SELECT *
        FROM licenses
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    return rows


def enable_license(key):

    conn = connect()

    cur = conn.execute("""
        UPDATE licenses
        SET enabled = 1
        WHERE license_key = ?
    """, (
        key.strip().upper(),
    ))

    conn.commit()

    changed = cur.rowcount

    conn.close()

    return changed > 0


def disable_license(key):

    conn = connect()

    cur = conn.execute("""
        UPDATE licenses
        SET enabled = 0
        WHERE license_key = ?
    """, (
        key.strip().upper(),
    ))

    conn.commit()

    changed = cur.rowcount

    conn.close()

    return changed > 0


def delete_license(key):

    key = key.strip().upper()

    conn = connect()

    conn.execute("""
        DELETE FROM activations
        WHERE license_key = ?
    """, (key,))

    cur = conn.execute("""
        DELETE FROM licenses
        WHERE license_key = ?
    """, (key,))

    conn.commit()

    changed = cur.rowcount

    conn.close()

    return changed > 0


def extend_license(key, minutes):

    key = key.strip().upper()

    row = get_license(key)

    if not row:
        return False

    if row["expires_at"] is None:
        return True

    expiry = datetime.fromisoformat(
        row["expires_at"]
    )

    if expiry < datetime.now():
        expiry = datetime.now()

    expiry += timedelta(
        minutes=minutes
    )

    conn = connect()

    conn.execute("""
        UPDATE licenses
        SET expires_at = ?
        WHERE license_key = ?
    """, (
        expiry.isoformat(),
        key
    ))

    conn.commit()
    conn.close()

    return True


def license_count():

    conn = connect()

    cur = conn.execute("""
        SELECT COUNT(*)
        FROM licenses
    """)

    value = cur.fetchone()[0]

    conn.close()

    return value


def active_license_count():

    conn = connect()

    cur = conn.execute("""
        SELECT COUNT(*)
        FROM licenses
        WHERE enabled = 1
    """)

    value = cur.fetchone()[0]

    conn.close()

    return value
