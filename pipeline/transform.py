import pandas as pd
from config import INDICATEURS

def transform(df):
    print("🔧 [TRANSFORM] Nettoyage et restructuration...")

    # Étape 1 : remettre à plat (stack des années)
    df = df.stack().reset_index()
    df.columns = ["pays", "indicateur", "annee", "valeur"]

    # Étape 2 : garder la valeur la plus récente par pays + indicateur
    df = (
        df.dropna(subset=["valeur"])
          .sort_values("annee", ascending=False)
          .groupby(["pays", "indicateur"])
          .first()
          .reset_index()
    )

    # Étape 3 : pivoter les indicateurs en colonnes
    df = df.pivot(index="pays", columns="indicateur", values="valeur")
    df = df.rename(columns=INDICATEURS)
    df = df.reset_index()

    # Étape 4 : ajouter la date de mise à jour
    df["date_maj"] = pd.Timestamp.today().strftime("%Y-%m-%d")

    print(f"✅ Données transformées : {df.shape}")
    return df