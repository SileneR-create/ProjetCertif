import pytest
import psycopg2
import os


# ─── FIXTURE CONNEXION ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pg_conn():
    """Ouvre une connexion PostgreSQL pour la session de tests.
    Skip automatiquement si le conteneur Docker est éteint (CI sans Docker).
    """
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=os.getenv("DB_NAME", "bdd_projet_certif"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password"),
        )
        yield conn
        conn.close()
    except (psycopg2.OperationalError, UnicodeDecodeError):
        pytest.skip(
            "PostgreSQL injoignable — vérifiez que Docker est lancé (`docker ps`) "
            "et que le port est disponible."
        )


# ─── TESTS STRUCTURE ─────────────────────────────────────────────────────────

def test_postgres_connection_and_tables(pg_conn):
    """C12 — Valider les jeux de données : structure de la BDD."""
    cursor = pg_conn.cursor()

    # RÈGLE 1 : La table des utilisateurs existe
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
    )
    assert cursor.fetchone()[0], "La table 'users' n'existe pas dans la base de données."

    # RÈGLE 2 : La table doit être requêtable
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    assert count >= 0, "Impossible de lire le contenu de la table 'users'."


# ─── TESTS QUALITÉ DES DONNÉES (C12) ────────────────────────────────────────

def test_destinations_table_not_empty(pg_conn):
    """C12 — Les données de destinations doivent exister en base (au moins 100 lignes)."""
    cursor = pg_conn.cursor()
    # Tente sur les tables candidates (selon le schéma du projet)
    for table in ("destinations", "villes", "cities"):
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
            (table,),
        )
        if cursor.fetchone()[0]:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            assert count >= 100, (
                f"La table '{table}' contient seulement {count} lignes — "
                "dataset insuffisant pour l'entraînement du modèle."
            )
            return
    pytest.skip("Aucune table de destinations trouvée — vérifier le schéma BDD.")


def test_no_null_in_critical_columns(pg_conn):
    """C12 — Valider les données : aucune valeur NULL dans les colonnes critiques du modèle ML."""
    cursor = pg_conn.cursor()

    # Vérifie si une table de données agrégées existe
    for table in ("destinations", "villes", "cities"):
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
            (table,),
        )
        if not cursor.fetchone()[0]:
            continue

        # Colonnes critiques pour le modèle KMeans/Random Forest
        critical_cols = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]
        for col in critical_cols:
            cursor.execute(
                f"SELECT EXISTS (SELECT FROM information_schema.columns "
                f"WHERE table_name = %s AND column_name = %s);",
                (table, col),
            )
            if not cursor.fetchone()[0]:
                continue  # colonne absente de cette table, on passe

            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL;")
            null_count = cursor.fetchone()[0]
            assert null_count == 0, (
                f"Colonne '{col}' dans '{table}' contient {null_count} valeurs NULL — "
                "le pipeline ETL doit imputer les valeurs manquantes avant stockage."
            )
        return
    pytest.skip("Aucune table de destinations trouvée — vérifier le schéma BDD.")
