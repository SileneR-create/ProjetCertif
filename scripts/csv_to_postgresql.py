import psycopg2
from sqlalchemy import create_engine
import pandas as pd
from DB_CONFIG import DB_CONFIG

# Création du moteur SQLAlchemy (nécessaire pour pandas .to_sql())
engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# --- Activites ---
df_act = pd.read_csv(r"..\DATA\processed\activites.csv")
df_filtred = df_act[['culture', 'adventure', 'nature', 'beaches', 'nightlife', 'cuisine', 'wellness', 'urban', 'seclusion']]
df_activ = pd.DataFrame(df_filtred.columns, columns=['nom_activite'])
df_activ.to_sql("Activites", engine, if_exists="append", index=False)

# --- Destinations ---
df_destination = pd.read_csv(r"..\DATA\processed\destinations.csv")
df_destination.to_sql("Destinations", engine, if_exists="append", index=False)

# --- Meteo ---
df_meteo = pd.read_csv(r"..\DATA\processed\meteo.csv")
df_meteo.to_sql("meteo", engine, if_exists="append", index=False)

# --- Indicateurs WorldBank ---
df_worldbank = pd.read_csv(r"..\DATA\processed\worldbank.csv")
df_worldbank.to_sql("Indicateurs_WorldBank", engine, if_exists="append", index=False)

# Fermeture du moteur
engine.dispose()