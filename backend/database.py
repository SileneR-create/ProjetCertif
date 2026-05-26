"""
database.py — Gestion de la base de données SQLite
Tables : users, favorites, search_history, profiles
"""

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime

DB_PATH = "travelmatch.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            salt        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            city          TEXT    NOT NULL,
            country       TEXT,
            month         INTEGER NOT NULL,
            score_pct     REAL,
            temp_avg      REAL,
            cluster_label TEXT,
            saved_at      TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, city, month)
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            preferences TEXT    NOT NULL,
            top_result  TEXT,
            searched_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            preferences TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, name)
        )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS user_interests (
        user_id     INTEGER PRIMARY KEY,
        interests   TEXT NOT NULL,
        updated_at  TEXT NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()


# ─── AUTH ───────────────────────────────────────────────────────────────────


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


"""
def register_user(username, email, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        salt = secrets.token_hex(16)
        hashed = _hash_password(password, salt)
        c.execute(
            "INSERT INTO users (username, email, password, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (username.strip(), email.strip().lower(), hashed, salt, datetime.now().isoformat())
        )
        conn.commit()
        return {"success": True, "user_id": c.lastrowid}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"success": False, "error": "Ce nom d'utilisateur est déjà pris."}
        if "email" in str(e):
            return {"success": False, "error": "Cet email est déjà utilisé."}
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
        """


def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
        user = c.fetchone()
        if not user:
            return {"success": False, "error": "Nom d'utilisateur introuvable."}
        if _hash_password(password, user["salt"]) != user["password"]:
            return {"success": False, "error": "Mot de passe incorrect."}
        return {"success": True, "user": dict(user)}
    finally:
        conn.close()


# ─── PROFILS ────────────────────────────────────────────────────────────────


def save_profile(user_id: int, name: str, preferences: dict) -> dict:
    """Crée ou met à jour un profil (upsert sur user_id + name)."""
    conn = get_connection()
    c = conn.cursor()
    try:
        now = datetime.now().isoformat()
        c.execute(
            """
            INSERT INTO profiles (user_id, name, preferences, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, name) DO UPDATE SET
                preferences = excluded.preferences,
                updated_at  = excluded.updated_at
        """,
            (user_id, name.strip(), json.dumps(preferences), now, now),
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_profiles(user_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM profiles WHERE user_id=? ORDER BY updated_at DESC", (user_id,)
    )
    rows = []
    for r in c.fetchall():
        row = dict(r)
        row["preferences"] = json.loads(row["preferences"])
        rows.append(row)
    conn.close()
    return rows


def delete_profile(profile_id: int, user_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "DELETE FROM profiles WHERE id=? AND user_id=?", (profile_id, user_id)
        )
        conn.commit()
        return {"success": True}
    finally:
        conn.close()


# ─── FAVORIS ────────────────────────────────────────────────────────────────


def add_favorite(user_id, city, country, month, score_pct, temp_avg, cluster_label):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT OR REPLACE INTO favorites
            (user_id, city, country, month, score_pct, temp_avg, cluster_label, saved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                city,
                country,
                month,
                score_pct,
                temp_avg,
                cluster_label,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def remove_favorite(user_id, city, month):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "DELETE FROM favorites WHERE user_id=? AND city=? AND month=?",
        (user_id, city, month),
    )
    conn.commit()
    conn.close()
    return {"success": True}


def get_favorites(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM favorites WHERE user_id=? ORDER BY saved_at DESC", (user_id,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def is_favorite(user_id, city, month):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND city=? AND month=?",
        (user_id, city, month),
    )
    result = c.fetchone() is not None
    conn.close()
    return result


# ─── HISTORIQUE ─────────────────────────────────────────────────────────────


def save_search(user_id, month, preferences, top_result):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO search_history (user_id, month, preferences, top_result, searched_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            user_id,
            month,
            json.dumps(preferences),
            top_result,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_search_history(user_id, limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM search_history WHERE user_id=?
        ORDER BY searched_at DESC LIMIT ?
    """,
        (user_id, limit),
    )
    rows = []
    for r in c.fetchall():
        row = dict(r)
        row["preferences"] = json.loads(row["preferences"])
        rows.append(row)
    conn.close()
    return rows


# ─── CENTRES D'INTÉRÊT ──────────────────────────────────────────────────────


def register_user(username, email, password, interests: dict):
    """Version étendue avec centres d'intérêt à l'inscription."""
    conn = get_connection()
    c = conn.cursor()
    try:
        salt = secrets.token_hex(16)
        hashed = _hash_password(password, salt)
        c.execute(
            "INSERT INTO users (username, email, password, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                username.strip(),
                email.strip().lower(),
                hashed,
                salt,
                datetime.now().isoformat(),
            ),
        )
        user_id = c.lastrowid
        # Sauvegarder les centres d'intérêt
        c.execute(
            """
            INSERT OR REPLACE INTO user_interests (user_id, interests, updated_at)
            VALUES (?, ?, ?)
        """,
            (user_id, json.dumps(interests), datetime.now().isoformat()),
        )
        conn.commit()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"success": False, "error": "Ce nom d'utilisateur est déjà pris."}
        if "email" in str(e):
            return {"success": False, "error": "Cet email est déjà utilisé."}
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_user_interests(user_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT interests FROM user_interests WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row["interests"])
    return {
        "nature": 3,
        "patrimoine": 3,
        "culture": 3,
        "restaurant": 3,
        "nightlife": 3,
        "loisirs": 3,
    }


def update_user_interests(user_id: int, interests: dict) -> dict:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT OR REPLACE INTO user_interests (user_id, interests, updated_at)
            VALUES (?, ?, ?)
        """,
            (user_id, json.dumps(interests), datetime.now().isoformat()),
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
