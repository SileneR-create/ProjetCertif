"""
database.py — Gestion de la base de données PostgreSQL
Utilisé exclusivement par le conteneur Backend (FastAPI)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Crée et retourne une connexion vers la base de données PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "bdd_projet_certif"),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "password"),
    )


def init_db():
    """Initialise les tables de la base de données si elles n'existent pas."""
    conn = get_connection()
    c = conn.cursor()

    # Table des utilisateurs
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INT DEFAULT 0
        )
    """
    )

    # Table de l'historique des recherches
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    c.close()
    conn.close()


# ─────────────────────────────────────────────
#  FONCTIONS POUR L'ADMINISTRATION
# ─────────────────────────────────────────────


def db_get_user_stats() -> dict:
    """Compte les utilisateurs globaux et admins."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    total_admins = c.fetchone()[0]

    c.close()
    conn.close()
    return {"total_users": total_users, "total_admins": total_admins}


def db_get_all_users() -> list:
    """Récupère tous les utilisateurs (format dictionnaire pour JSON/API)."""
    conn = get_connection()
    # RealDictCursor permet de récupérer les lignes sous forme de dict {colonne: valeur}
    c = conn.cursor(cursor_factory=RealDictCursor)

    c.execute("SELECT id, username, email, is_admin FROM users ORDER BY id DESC")
    users = c.fetchall()

    c.close()
    conn.close()
    return users


def db_delete_user(user_id: int):
    """Supprime un utilisateur à partir de son ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    c.close()
    conn.close()


def db_get_search_history() -> list:
    """Récupère l'historique complet avec jointure pour afficher le nom de l'user."""
    conn = get_connection()
    c = conn.cursor(cursor_factory=RealDictCursor)

    c.execute(
        """
        SELECT h.id, u.username, h.query, h.created_at 
        FROM search_history h
        JOIN users u ON h.user_id = u.id
        ORDER BY h.created_at DESC
    """
    )
    history = c.fetchall()

    # Conversion des objets datetime en chaînes de caractères pour sérialisation JSON
    for row in history:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    c.close()
    conn.close()
    return history
