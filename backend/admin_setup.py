"""
admin_setup.py
Script pour créer/promouvoir le premier administrateur
Compatible PostgreSQL et SQLite
"""

import getpass
from backend.database_pg import get_connection


def promote_user_to_admin(username: str):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Vérifier si l'utilisateur existe
        cursor.execute(
            "SELECT id, username, is_admin FROM users WHERE username = %s",
            (username,),
        )

        user = cursor.fetchone()

        if not user:
            print(f"❌ Utilisateur '{username}' introuvable.")
            return

        # Déjà admin
        if user["is_admin"]:
            print(f"✅ '{username}' est déjà administrateur.")
            return

        # Promotion admin
        cursor.execute(
            "UPDATE users SET is_admin = TRUE WHERE username = %s",
            (username,),
        )

        conn.commit()

        print(f"✅ '{username}' est maintenant administrateur.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur : {e}")

    finally:
        conn.close()


def list_users():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, username, email, is_admin
            FROM users
            ORDER BY created_at
            """
        )

        users = cursor.fetchall()

        print("\n👥 Utilisateurs disponibles :\n")

        for user in users:
            badge = "🛠️ ADMIN" if user["is_admin"] else "👤 USER"

            print(f"[{user['id']}] " f"{user['username']} " f"({user['email']}) " f"{badge}")

        print()

    except Exception as e:
        print(f"❌ Erreur : {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("\n🛠️ Setup Administrateur TravelMatch\n")

    list_users()

    username = input("Nom d'utilisateur à promouvoir admin : ").strip()

    if not username:
        print("❌ Nom invalide.")
        exit()

    confirmation = input(f"Confirmer promotion de '{username}' ? (y/n) : ").lower()

    if confirmation == "y":
        promote_user_to_admin(username)
    else:
        print("❌ Opération annulée.")
