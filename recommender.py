import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
#  FEATURE GROUPS
# ─────────────────────────────────────────────

ACTIVITY_FEATURES = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]

COMFORT_FEATURES = [
    "Accès électricité (% pop)",
    "Accès Internet (% pop)",
    "Accès eau potable (% pop)",
    "Médecins (pour 1000 habitants)",
    "Dépenses santé par habitant (USD)",
    "Espérance de vie (années)",
]

ECONOMIC_FEATURES = [
    "PIB par habitant (USD)",
    "Pauvreté < 3$/jour (% pop)",
    "Revenu moyen par habitant ($/jour)",
]

TOURISM_FEATURES = [
    "Arrivées touristes internationaux (nb)",
    "Recettes tourisme (USD)",
    "valeur",
]

ALL_MODEL_FEATURES = ACTIVITY_FEATURES + COMFORT_FEATURES + ECONOMIC_FEATURES + TOURISM_FEATURES

MONTH_NAMES = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}


# ─────────────────────────────────────────────
#  FEATURE ENGINEERING
# ─────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Crée des indices composites normalisés entre 0 et 100."""
    df = df.copy()

    # Indice confort sanitaire (0-100)
    comfort_cols = [
        "Accès électricité (% pop)", "Accès Internet (% pop)",
        "Accès eau potable (% pop)", "Espérance de vie (années)"
    ]
    available = [c for c in comfort_cols if c in df.columns]
    if available:
        normed = df[available].apply(
            lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9)
        )
        df["indice_confort"] = (normed.mean(axis=1) * 100).round(1)

    # Indice sécurité / richesse (0-100)
    if "PIB par habitant (USD)" in df.columns and "Pauvreté < 3$/jour (% pop)" in df.columns:
        pib_norm = (df["PIB par habitant (USD)"] - df["PIB par habitant (USD)"].min()) / \
                   (df["PIB par habitant (USD)"].max() - df["PIB par habitant (USD)"].min() + 1e-9)
        pov_norm = (df["Pauvreté < 3$/jour (% pop)"] - df["Pauvreté < 3$/jour (% pop)"].min()) / \
                   (df["Pauvreté < 3$/jour (% pop)"].max() - df["Pauvreté < 3$/jour (% pop)"].min() + 1e-9)
        df["indice_securite"] = ((pib_norm * 0.6 + (1 - pov_norm) * 0.4) * 100).round(1)

    # Indice popularité touristique (0-100)
    if "Arrivées touristes internationaux (nb)" in df.columns:
        arr = df["Arrivées touristes internationaux (nb)"]
        df["indice_tourisme"] = ((arr - arr.min()) / (arr.max() - arr.min() + 1e-9) * 100).round(1)

    return df


# ─────────────────────────────────────────────
#  CLUSTERING (pour visualisation carte)
# ─────────────────────────────────────────────

def build_clusters(df_month: pd.DataFrame, n_clusters: int = 6) -> pd.DataFrame:
    """Attribue un cluster de type de destination à chaque ville."""
    cluster_features = ACTIVITY_FEATURES + ["indice_confort", "indice_securite", "temp_avg"]
    available = [f for f in cluster_features if f in df_month.columns]

    X = df_month[available].fillna(df_month[available].median())
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_month = df_month.copy()
    df_month["cluster"] = km.fit_predict(X_scaled)

    cluster_labels = _label_clusters(km.cluster_centers_, available, n_clusters)
    df_month["cluster_label"] = df_month["cluster"].map(cluster_labels)

    return df_month


def _label_clusters(centers, feature_names, n_clusters):
    icons = ["🌿", "🏛️", "🎭", "🌊", "🏙️", "🎉"]
    names = ["Nature & Aventure", "Patrimoine & Histoire", "Culture & Arts",
             "Détente & Plages", "Métropole Moderne", "Fête & Nightlife"]
    return {i: f"{icons[i % len(icons)]} {names[i % len(names)]}" for i in range(n_clusters)}


# ─────────────────────────────────────────────
#  SCORE TEMPÉRATURE
# ─────────────────────────────────────────────

def _temp_score(city_temp: float, user_temp: float, tolerance: float = 8.0) -> float:
    """Score entre 0 et 1 — 1 si température idéale, décroît avec l'écart."""
    diff = abs(city_temp - user_temp)
    return float(max(0.0, 1.0 - diff / tolerance))


# ─────────────────────────────────────────────
#  SCORE CONFORT / SÉCURITÉ
# ─────────────────────────────────────────────

def _index_score(city_val: float, user_val: float, tolerance: float = 30.0) -> float:
    """Score entre 0 et 1 pour les indices 0-100."""
    diff = abs(city_val - user_val)
    return float(max(0.0, 1.0 - diff / tolerance))


# ─────────────────────────────────────────────
#  MOTEUR DE RECOMMANDATION
# ─────────────────────────────────────────────

def recommend(
    df: pd.DataFrame,
    month: int,
    user_prefs: dict,
    top_n: int = 10,
    weight_activities: float = 0.60,
    weight_temp: float = 0.20,
    weight_comfort: float = 0.10,
    weight_security: float = 0.10,
) -> pd.DataFrame:
    """
    Paramètres
    ----------
    df               : dataset complet (toutes villes, tous mois)
    month            : mois choisi (1-12)
    user_prefs       : dict avec les préférences utilisateur :
                       {
                         "temp_avg"        : float (°C souhaités),
                         "nature"          : float (0-5),
                         "patrimoine"      : float (0-5),
                         "culture"         : float (0-5),
                         "restaurant"      : float (0-5),
                         "nightlife"       : float (0-5),
                         "loisirs"         : float (0-5),
                         "indice_confort"  : float (0-100),
                         "indice_securite" : float (0-100),
                       }
    weight_*         : pondération de chaque composante (somme = 1)
    """
    # 1. Filtrer sur le mois
    df_m = df[df["month"] == month].copy()
    df_m = engineer_features(df_m)
    df_m = df_m.reset_index(drop=True)

    # ── SCORE ACTIVITÉS (distance euclidienne, 0-1) ──────────────────
    act_cols = [f for f in ACTIVITY_FEATURES if f in df_m.columns]

    # Normaliser les activités du dataset entre 0 et 1
    scaler_act = MinMaxScaler()
    X_act = pd.DataFrame(
        scaler_act.fit_transform(df_m[act_cols].fillna(0)),
        columns=act_cols
    )

    # Vecteur utilisateur : sliders 0-5 → 0-1
    user_act = np.array([user_prefs.get(f, 0) / 5.0 for f in act_cols]).reshape(1, -1)

    # Distance euclidienne → score (plus proche = meilleur)
    dists = euclidean_distances(user_act, X_act)[0]
    max_dist = np.sqrt(len(act_cols))  # distance max théorique (tous à 0 vs tous à 1)
    score_act = 1.0 - (dists / max_dist)

    # ── SCORE TEMPÉRATURE (0-1) ───────────────────────────────────────
    user_temp = user_prefs.get("temp_avg", 20)
    score_temp = df_m["temp_avg"].apply(
        lambda t: _temp_score(t, user_temp, tolerance=10)
    ).values

    # ── SCORE CONFORT (0-1) ───────────────────────────────────────────
    if "indice_confort" in df_m.columns:
        user_confort = user_prefs.get("indice_confort", 50)
        score_confort = df_m["indice_confort"].apply(
            lambda v: _index_score(v, user_confort, tolerance=40)
        ).values
    else:
        score_confort = np.ones(len(df_m))

    # ── SCORE SÉCURITÉ (0-1) ──────────────────────────────────────────
    if "indice_securite" in df_m.columns:
        user_secu = user_prefs.get("indice_securite", 50)
        score_secu = df_m["indice_securite"].apply(
            lambda v: _index_score(v, user_secu, tolerance=40)
        ).values
    else:
        score_secu = np.ones(len(df_m))

    # ── SCORE FINAL PONDÉRÉ ───────────────────────────────────────────
    df_m["score_activites"] = score_act
    df_m["score_temp"]      = score_temp
    df_m["score_confort"]   = score_confort
    df_m["score_securite"]  = score_secu

    df_m["score"] = (
        weight_activities * score_act   +
        weight_temp       * score_temp  +
        weight_comfort    * score_confort +
        weight_security   * score_secu
    )

    # Normaliser en pourcentage 0-100
    df_m["score_pct"] = (df_m["score"] / df_m["score"].max() * 100).round(1)

    # ── CLUSTERING ────────────────────────────────────────────────────
    df_m = build_clusters(df_m)

    # ── TOP N ─────────────────────────────────────────────────────────
    results = df_m.nlargest(top_n, "score").reset_index(drop=True)
    results["rang"] = range(1, len(results) + 1)

    return results