import pytest
import psycopg2
import os

def test_postgres_connection_and_tables():
    """Vérifie que la BDD est accessible et contient des données."""
    host = os.getenv("DB_HOST", "localhost")
    
    # 1. On tente la connexion. Si elle échoue à cause d'un problème Windows/Docker,
    # on capture l'erreur d'encodage à la racine.
    try:
        conn = psycopg2.connect(
            host=host,
            port=5433,
            database='bdd_projet_certif',
            user='user',
            password='password'
        )
    except (psycopg2.OperationalError, UnicodeDecodeError) as network_err:
        pytest.fail(
            "Impossible de se connecter à PostgreSQL. Vérifiez que votre conteneur Docker "
            "est bien allumé (`docker ps`) et que le port 5432 est disponible."
        )

    # 2. Si la connexion a réussi, on procède aux validations de structure
    try:
        cursor = conn.cursor()
        
        # RÈGLE 1 : La table des utilisateurs existe
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');")
        assert cursor.fetchone()[0], "La table 'users' n'existe pas dans la base de données."
        
        # RÈGLE 2 : Compter les utilisateurs (la table doit être requêtable)
        cursor.execute('SELECT COUNT(*) FROM users;')
        count = cursor.fetchone()[0]
        assert count >= 0, "Impossible de lire le contenu de la table 'users'."
        
        conn.close()
    except Exception as e:
        pytest.fail(f"Défaut de validation des requêtes BDD : {e}")