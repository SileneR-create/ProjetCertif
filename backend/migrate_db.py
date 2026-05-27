"""
migrate_db.py
Migration SQLite -> PostgreSQL
"""

import sqlite3
from backend.database_pg import get_connection


SQLITE_DB_PATH = "travelmatch.db"


TABLES = [
    "users",
    "profiles",
    "favorites",
    "search_history",
    "user_interests",
]


def fetch_sqlite_data(table_name):
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    cursor = sqlite_conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")

    rows = [dict(row) for row in cursor.fetchall()]

    sqlite_conn.close()

    return rows


def migrate_table(table_name):
    print(f"\n📦 Migration table : {table_name}")

    rows = fetch_sqlite_data(table_name)

    if not rows:
        print("⚠️ Aucune donnée.")
        return

    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    try:
        columns = rows[0].keys()

        column_names = ", ".join(columns)

        placeholders = ", ".join(["%s"] * len(columns))

        query = f"""
            INSERT INTO {table_name}
            ({column_names})
            VALUES ({placeholders})
        """

        inserted = 0

        for row in rows:
            values = [row[col] for col in columns]

            try:
                pg_cursor.execute(query, values)
                inserted += 1

            except Exception as row_error:
                print(f"⚠️ Ligne ignorée : {row_error}")

        pg_conn.commit()

        print(f"✅ {inserted} lignes migrées.")

    except Exception as e:
        pg_conn.rollback()
        print(f"❌ Erreur migration : {e}")

    finally:
        pg_conn.close()


def run_migration():
    print("\n🚀 Migration SQLite → PostgreSQL\n")

    for table in TABLES:
        migrate_table(table)

    print("\n✅ Migration terminée.\n")


if __name__ == "__main__":
    run_migration()
