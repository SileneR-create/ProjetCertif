import sqlite3

# Connexion à la base de données
conn = sqlite3.connect("travelmatch.db")
cursor = conn.cursor()

try:
    # 1. On ajoute la colonne 'is_admin' à la table 'users'
    # On met DEFAULT 0 pour que tous les utilisateurs existants soient 'non-admin' par défaut
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    print("Succès : La colonne 'is_admin' a été ajoutée.")
except sqlite3.OperationalError:
    # Si vous relancez le script, il dira que la colonne existe déjà
    print("Note : La colonne 'is_admin' existe déjà.")

# 2. On donne les droits admin à votre compte 'fabrice'
cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
conn.commit()

# Vérification
cursor.execute("SELECT username, is_admin FROM users WHERE username = 'admin'")
result = cursor.fetchone()
print(f"Vérification : L'utilisateur {result[0]} a le statut admin = {result[1]}")

conn.close()