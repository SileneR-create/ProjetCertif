import sqlite3
import pandas as pd

conn = sqlite3.connect(r"..\database\BDD_Projet_Certif.db")

df_act = pd.read_csv(r"..\DATA\processed\activites.csv")
df_filtred = df_act[['culture', 'adventure', 'nature', 'beaches', 'nightlife', 'cuisine', 'wellness', 'urban', 'seclusion']]
df_activ = pd.DataFrame(df_filtred.columns, columns=['nom_activite'])
df_activ.to_sql("Activites", conn, if_exists="append", index=False)

df_destination = pd.read_csv(r"..\DATA\processed\destinations.csv")
df_destination.to_sql("Destinations", conn, if_exists = "append", index = False)

df_meteo = pd.read_csv(r"..\DATA\processed\meteo.csv")
#df_meteo = df_meteo.drop(columns=["country"])
df_meteo.to_sql("meteo", conn, if_exists = "append", index = False)

df_worldbank = pd.read_csv(r"..\DATA\processed\worldbank.csv")
df_worldbank.to_sql("Indicateurs_WorldBank", conn, if_exists="append", index=False)


conn.close()