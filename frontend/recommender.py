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


# ─── LOGIQUE MACHINE LEARNING ──────────────────────────────────────

def train_ml_engine(df):
    """Calcule les clusters et entraîne le Random Forest."""
    # Groupement par ville pour l'identité ADN
    city_group = df.groupby('city')[ACTIVITY_FEATURES].mean().reset_index()
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(city_group[ACTIVITY_FEATURES])
    
    # 1. K-Means : Identifie les types de destinations
    kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    city_group['cluster_id'] = kmeans.fit_predict(X_scaled)
    
    # 2. Random Forest : Prédit le cluster idéal selon les entrées utilisateur
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(city_group[ACTIVITY_FEATURES], city_group['cluster_id'])
    
    return city_group[['city', 'cluster_id']], rf

def engineer_features(df):
    """Ta fonction de nettoyage originale adaptée."""
    df = df.copy()
    cols_to_fix = ACTIVITY_FEATURES + ["temp_avg", "PIB par habitant (USD)"]
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def recommend(df, month, user_prefs, top_n=10, cluster_bonus_id=None):
    # Initialisation IA
    city_clusters, rf_model = train_ml_engine(df)
    
    # Prédiction IA du cluster idéal
    user_vector = np.array([[user_prefs.get(f, 3) * 20 for f in ACTIVITY_FEATURES]])
    ideal_cluster_id = rf_model.predict(user_vector)[0]
    
    # Filtrage par mois
    df_m = df[df["month"] == month].copy()
    df_m = engineer_features(df_m)
    df_m = df_m.merge(city_clusters, on='city', how='left')

    # SCORING
    # Score Température (Ecart max 15°C)
    score_temp = 1.0 - (np.abs(df_m["temp_avg"] - user_prefs.get("temp_avg", 25)) / 15).clip(0, 1)
    
    # Score Activités
    act_diffs = [np.abs(df_m[f] - (user_prefs.get(f, 3) * 20)) / 100 for f in ACTIVITY_FEATURES]
    score_act = 1.0 - (sum(act_diffs) / len(ACTIVITY_FEATURES))

    # Score IA (Match avec le cluster prédit par Random Forest)
    score_ia = (df_m['cluster_id'] == ideal_cluster_id).astype(float)

    # Pondération (33% Temp, 33% Act, 34% IA)
    df_m["score"] = (score_temp * 0.33) + (score_act * 0.33) + (score_ia * 0.34)
    df_m["score_pct"] = (df_m["score"] * 100).round(1)
    
    # Labels pour l'UI
    cluster_labels = {0:"🌿 Nature", 1:"🏛️ Patrimoine", 2:"🎭 Culture", 3:"🌊 Détente", 4:"🏙️ Urbain", 5:"🎉 Vie Nocturne"}
    df_m["cluster_label"] = df_m["cluster_id"].map(cluster_labels)

    # --- INDISPENSABLE POUR TON APP.PY ---
    results = df_m.nlargest(top_n, "score").reset_index(drop=True)
    results["rang"] = results.index + 1 
    
    return results

