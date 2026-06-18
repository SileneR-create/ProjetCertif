"""Construction du jeu de données « destinations » pour l'étude de clustering.

Source : ``DATA/raw/Worldwide_Travel_Cities.csv`` (560 villes, données complètes,
0 valeur manquante) — bien plus riche que ``data_clean.csv`` (84 villes, 6
features dérivées).

On distingue volontairement deux rôles :

* **Features de clustering** = les 9 dimensions d'activités (l'« ADN » de la
  destination), échelle 1–5, homogènes et sans NA.
* **Variables descriptives** (budget, climat, région) = utilisées UNIQUEMENT
  pour profiler / expliquer les clusters, **pas** pour les former. Raison de
  cohérence : le recommandeur note déjà séparément la température et le budget ;
  les inclure dans le clustering reviendrait à compter deux fois la même
  information et brouillerait l'interprétation des archétypes.
"""

import os
import json

import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(ROOT_DIR, "DATA", "raw", "Worldwide_Travel_Cities.csv")

# 9 dimensions d'activités (features de clustering)
ACTIVITY_FEATURES = [
    "culture",
    "adventure",
    "nature",
    "beaches",
    "nightlife",
    "cuisine",
    "wellness",
    "urban",
    "seclusion",
]

# Budget ordinal pour le profilage descriptif
BUDGET_ORDER = {"Budget": 1, "Mid-range": 2, "Luxury": 3}


def _annual_temp(raw: str):
    """Extrait (température moyenne annuelle, amplitude saisonnière) du JSON mensuel."""
    try:
        months = json.loads(raw)
        avgs = [m["avg"] for m in months.values()]
        return float(np.mean(avgs)), float(max(avgs) - min(avgs))
    except Exception:
        return np.nan, np.nan


def build_destination_features(path: str = RAW_PATH):
    """Charge et prépare le jeu de données destinations.

    Retourne un triplet :
      * ``cities``      : identité (id, city, country, region, lat, lon) ;
      * ``X``           : DataFrame des 9 activités (échelle 1–5, brut) ;
      * ``descriptive`` : variables de profilage (budget, climat, région).
    """
    df = pd.read_csv(path)

    temps = df["avg_temp_monthly"].apply(_annual_temp)
    df["temp_annual_avg"] = [t[0] for t in temps]
    df["temp_seasonality"] = [t[1] for t in temps]
    df["budget_num"] = df["budget_level"].map(BUDGET_ORDER)

    cities = df[["id", "city", "country", "region", "latitude", "longitude"]].reset_index(drop=True)
    X = df[ACTIVITY_FEATURES].astype(float).reset_index(drop=True)
    descriptive = df[
        ["budget_level", "budget_num", "temp_annual_avg", "temp_seasonality", "region"]
    ].reset_index(drop=True)

    return cities, X, descriptive
