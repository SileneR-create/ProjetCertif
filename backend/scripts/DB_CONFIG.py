import os

DB_CONFIG = {
    # os.getenv cherche la variable injectée par Docker-compose.
    # Si elle n'existe pas (en local), il se rabat sur "localhost"
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "bdd_projet_certif"),
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
}
