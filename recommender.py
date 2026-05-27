import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import euclidean_distances
import warnings

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
#  FEATURE GROUPS
# ─────────────────────────────────────────────

ACTIVITY_FEATURES = [
    "nature",
    "patrimoine",
    "culture",
    "restaurant",
    "nightlife",
    "loisirs",
]

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
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}


# ─── LOGIQUE MACHINE LEARNING ──────────────────────────────────────


def train_ml_engine(df):
    """Calcule les clusters et entraîne le Random Forest."""
    # Groupement par ville pour l'identité ADN
    city_group = df.groupby("city")[ACTIVITY_FEATURES].mean().reset_index()
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(city_group[ACTIVITY_FEATURES])

    # 1. K-Means : Identifie les types de destinations
    kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    city_group["cluster_id"] = kmeans.fit_predict(X_scaled)

    # 2. Random Forest : Prédit le cluster idéal selon les entrées utilisateur
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(city_group[ACTIVITY_FEATURES], city_group["cluster_id"])

    return city_group[["city", "cluster_id"]], rf


def engineer_features(df):
    """Ta fonction de nettoyage originale adaptée."""
    df = df.copy()
    cols_to_fix = ACTIVITY_FEATURES + ["temp_avg", "PIB par habitant (USD)"]
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def recommend(df, month, user_prefs, top_n=10, cluster_bonus_id=None):
    # Initialisation IA
    city_clusters, rf_model = train_ml_engine(df)

    # Prédiction IA du cluster idéal
    user_vector = np.array([[user_prefs.get(f, 3) * 20 for f in ACTIVITY_FEATURES]])
    ideal_cluster_id = rf_model.predict(user_vector)[0]

    # ─────────────────────────────────────────────────────────────
    # FILTRAGE PAR MOIS
    # ─────────────────────────────────────────────────────────────
    df_m = df[df["month"] == month].copy()
    df_m = engineer_features(df_m)
    df_m = df_m.merge(city_clusters, on="city", how="left")

    # ─────────────────────────────────────────────────────────────
    # FILTRAGE PAR BUDGET (SOFT - avec pénalité, pas strict)
    # ─────────────────────────────────────────────────────────────
    revenu_col = "Revenu moyen par habitant ($/jour)"
    budget_label = user_prefs.get("budget_label", None)

    if budget_label and revenu_col in df_m.columns:
        q1 = df[revenu_col].quantile(0.25)
        q2 = df[revenu_col].quantile(0.50)
        q3 = df[revenu_col].quantile(0.75)

        budget_filters = {
            "🎒 Budget serré": (0, q1),
            "✈️ Moyen": (q1, q2),
            "🏨 Confortable": (q2, q3),
            "💎 Luxe": (q3, float("inf")),
        }

        if budget_label in budget_filters:
            min_rev, max_rev = budget_filters[budget_label]
            df_m["budget_match"] = ((df_m[revenu_col] >= min_rev) & (df_m[revenu_col] <= max_rev)).astype(float)
            # 1.0 si dans la plage, 0.7 sinon
            df_m["budget_match"] = df_m["budget_match"].replace(0, 0.7)
    else:
        df_m["budget_match"] = 1.0

    # ─────────────────────────────────────────────────────────────
    # SCORING - PART 1 : TEMPÉRATURE
    # ─────────────────────────────────────────────────────────────
    temp_target = user_prefs.get("temp_avg", 25)
    temp_diff = np.abs(df_m["temp_avg"] - temp_target)

    # Courbe douce : parfait jusqu'à 5°C, puis pénalité progressive
    score_temp = np.where(temp_diff <= 5, 1.0, 1.0 - (temp_diff - 5) / 20).clip(0, 1)

    # ─────────────────────────────────────────────────────────────
    # SCORING - PART 2 : ACTIVITÉS (avec distance euclidienne)
    # ─────────────────────────────────────────────────────────────
    user_activities = np.array([[user_prefs.get(f, 3) * 20 for f in ACTIVITY_FEATURES]])
    city_activities = df_m[ACTIVITY_FEATURES].values

    distances = euclidean_distances(city_activities, user_activities).flatten()
    max_distance = np.sqrt(len(ACTIVITY_FEATURES) * (100**2))
    score_act = (1.0 - (distances / max_distance)).clip(0, 1)

    # ─────────────────────────────────────────────────────────────
    # SCORING - PART 3 : CLUSTER (IA + bonus utilisateur)
    # ─────────────────────────────────────────────────────────────
    score_ia = (df_m["cluster_id"] == ideal_cluster_id).astype(float)

    # Bonus si l'utilisateur a choisi un type de destination
    if cluster_bonus_id is not None:
        score_ia = np.where(
            df_m["cluster_id"] == cluster_bonus_id,
            1.0,  # Priorité au choix utilisateur
            score_ia * 0.5,  # Fallback au cluster IA (50% du score)
        )

    # ─────────────────────────────────────────────────────────────
    # SCORING - PART 4 : INFRASTRUCTURE (4 dimensions séparées)
    # "Au minimum ce niveau"
    # ─────────────────────────────────────────────────────────────

    # 1️⃣ ÉLECTRICITÉ
    indice_electricite = user_prefs.get("indice_electricite", 80)
    if "Accès électricité (% pop)" in df_m.columns:
        score_electricite = np.minimum(df_m["Accès électricité (% pop)"] / indice_electricite, 1.0)
    else:
        score_electricite = np.ones(len(df_m))

    # 2️⃣ INTERNET
    indice_internet = user_prefs.get("indice_internet", 70)
    if "Accès Internet (% pop)" in df_m.columns:
        score_internet = np.minimum(df_m["Accès Internet (% pop)"] / indice_internet, 1.0)
    else:
        score_internet = np.ones(len(df_m))

    # 3️⃣ EAU POTABLE
    indice_eau = user_prefs.get("indice_eau", 85)
    if "Accès eau potable (% pop)" in df_m.columns:
        score_eau = np.minimum(df_m["Accès eau potable (% pop)"] / indice_eau, 1.0)
    else:
        score_eau = np.ones(len(df_m))

    # 4️⃣ MÉDECINS
    indice_medecins = user_prefs.get("indice_medecins", 2.0)  # Pour 1000 hab
    if "Médecins (pour 1000 habitants)" in df_m.columns:
        score_medecins = np.minimum(df_m["Médecins (pour 1000 habitants)"] / indice_medecins, 1.0)
    else:
        score_medecins = np.ones(len(df_m))

    # ─────────────────────────────────────────────────────────────
    # COMBINAISON FINALE DES SCORES
    # ─────────────────────────────────────────────────────────────
    # Pondération mise à jour (4 infrastructure au lieu de 2)
    df_m["score"] = (
        (score_temp * 0.25)
        + (score_act * 0.30)
        + (score_ia * 0.20)
        + (score_electricite * 0.05)  # 4 dimensions, 5% chacune = 20%
        + (score_internet * 0.05)
        + (score_eau * 0.05)
        + (score_medecins * 0.05)
        + 0.00
    )

    # Appliquer le budget comme multiplicateur (soft penalty)
    df_m["score"] = df_m["score"] * df_m["budget_match"]

    # ⚠️ SUPPRIMER la normalisation min-max (garder les vraies valeurs)
    df_m["score_pct"] = (df_m["score"] * 100).round(1)

    # ─────────────────────────────────────────────────────────────
    # COMBINAISON FINALE DES SCORES
    # ─────────────────────────────────────────────────────────────
    # Pondération (25% chacun pour les principaux, 12.5% pour confort/sécu, 10% pour budget)
    df_m["score"] = (
        (score_temp * 0.25)
        + (score_act * 0.30)
        + (score_ia * 0.20)
        + (score_electricite * 0.05)
        + (score_internet * 0.05)
        + (score_eau * 0.05)
        + (score_medecins * 0.05)
        + 0.00
    )

    # Appliquer le budget comme multiplicateur (soft penalty)
    df_m["score"] = df_m["score"] * df_m["budget_match"]

    # Normaliser entre 0 et 1
    df_m["score"] = (df_m["score"] / 1.0).clip(0, 1)  # Garder entre 0 et 1
    df_m["score_pct"] = (df_m["score"] * 100).round(1)

    # ─────────────────────────────────────────────────────────────
    # LABELS ET RÉSULTATS
    # ─────────────────────────────────────────────────────────────
    cluster_labels = {
        0: "🌿 Nature",
        1: "🏛️ Patrimoine",
        2: "🎭 Culture",
        3: "🌊 Détente",
        4: "🏙️ Urbain",
        5: "🎉 Vie Nocturne",
    }
    df_m["cluster_label"] = df_m["cluster_id"].map(cluster_labels)

    # Top N résultats
    results = df_m.nlargest(top_n, "score").reset_index(drop=True)
    results["rang"] = results.index + 1

    return results
