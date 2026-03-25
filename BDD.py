import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "BDD_Projet_Certif.db"
SCHEMA   = BASE_DIR / "schema.sql"

def connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row  # accès aux colonnes par nom : row["email"]
    return conn

def init_db() -> None:
    try:
        conn = connexion()
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        conn.close()
        print("BDD initialisée avec succès ma puce.")
    except Exception as e:
        print(f"Erreur initialisation BDD : {e}")

if __name__ == "__main__":
    init_db()