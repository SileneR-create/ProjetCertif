import sqlite3
import os
from config import OUTPUT_CSV, OUTPUT_DB, TABLE_NAME

def load(df):
    print("💾 [LOAD] Sauvegarde des données...")

    # Créer le dossier output si nécessaire
    os.makedirs("output", exist_ok=True)

    # Sauvegarde CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ CSV sauvegardé : {OUTPUT_CSV}")

    # Sauvegarde base de données SQLite
    conn = sqlite3.connect(OUTPUT_DB)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()
    print(f"✅ Base de données sauvegardée : {OUTPUT_DB} (table: {TABLE_NAME})")