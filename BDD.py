import sqlite3

def connexion():
    return sqlite3.connect('BDD_Projet_Certif.db')

def init_db():
    try:
        with connexion() as conn:
            cursor = conn.cursor()

            with open("schema.sql", "r") as f:
                sql = f.read()

            cursor.executescript(sql)

    except Exception as e:
        print(f"Erreur initialisation BDD : {e}")