import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.pipeline import Pipeline
import os
import warnings

warnings.filterwarnings("ignore")

_CACHE: dict | None = None
_MLFLOW_EXPERIMENT = "TravelMatch_Recommender"

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
    """Calcule les clusters et entraîne le Random Forest.

    Signature publique inchangée : retourne (city_clusters, rf).
    """
    city_clusters, rf, _, _ = _train_full_engine(df)
    return city_clusters, rf


def _train_full_engine(df):
    """Comme train_ml_engine mais retourne aussi scaler et kmeans pour MLflow."""
    city_group = df.groupby("city")[ACTIVITY_FEATURES].mean().reset_index()
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(city_group[ACTIVITY_FEATURES])

    kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    city_group["cluster_id"] = kmeans.fit_predict(X_scaled)

    rf = RandomForestClassifier(n_estimators=100, random_state=42, oob_score=True)
    rf.fit(city_group[ACTIVITY_FEATURES], city_group["cluster_id"])

    return city_group[["city", "cluster_id"]], rf, scaler, kmeans


def _try_load_from_mlflow(df: pd.DataFrame) -> dict | None:
    """Charge le meilleur run depuis TravelMatch_Recommender.

    Cherche le run avec le meilleur rf_oob_score, charge le Pipeline de
    clustering (scaler + kmeans) et le RandomForest, puis recalcule les
    cluster_id des villes sur les données courantes.

    Retourne {city_clusters, rf} ou None si MLflow est indisponible / aucun run.
    """
    try:
        import mlflow
        import mlflow.sklearn
        uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        client = mlflow.tracking.MlflowClient()

        exp = client.get_experiment_by_name(_MLFLOW_EXPERIMENT)
        if exp is None:
            return None

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="tags.status = 'ready'",
            order_by=["metrics.rf_oob_score DESC"],
            max_results=1,
        )
        if not runs:
            return None

        best = runs[0]
        run_id = best.info.run_id

        cluster_pipe = mlflow.sklearn.load_model(f"runs:/{run_id}/cluster_pipeline")
        rf = mlflow.sklearn.load_model(f"runs:/{run_id}/rf_model")

        city_group = df.groupby("city")[ACTIVITY_FEATURES].mean().reset_index()
        city_group["cluster_id"] = cluster_pipe.predict(city_group[ACTIVITY_FEATURES])

        oob = best.data.metrics.get("rf_oob_score", 0.0)
        print(f"✅ Modèle chargé depuis MLflow | run={run_id[:8]} | oob={oob:.3f}")
        return {"city_clusters": city_group[["city", "cluster_id"]], "rf": rf}

    except Exception as e:
        print(f"⚠️ Chargement MLflow échoué ({e}) → entraînement local")
        return None


def _log_to_mlflow(rf, scaler, kmeans, city_clusters: pd.DataFrame) -> None:
    """Persiste le modèle entraîné dans MLflow (best-effort).

    Sauvegarde un Pipeline (scaler + kmeans) et le RandomForest sous
    l'expérience TravelMatch_Recommender. En cas d'échec (MLflow hors ligne,
    permission refusée, etc.), un message est affiché mais l'exception est avalée
    pour ne pas bloquer le service.
    """
    try:
        import mlflow
        import mlflow.sklearn
        uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(_MLFLOW_EXPERIMENT)

        example = pd.DataFrame([{f: 60.0 for f in ACTIVITY_FEATURES}])

        with mlflow.start_run(run_name="recommender_local"):
            mlflow.set_tag("status", "ready")
            mlflow.log_param("n_clusters", 6)
            mlflow.log_param("n_cities", len(city_clusters))
            mlflow.log_param("features", ",".join(ACTIVITY_FEATURES))
            if hasattr(rf, "oob_score_"):
                mlflow.log_metric("rf_oob_score", float(rf.oob_score_))

            cluster_pipe = Pipeline([("scaler", scaler), ("kmeans", kmeans)])
            mlflow.sklearn.log_model(cluster_pipe, name="cluster_pipeline", input_example=example)
            mlflow.sklearn.log_model(rf, name="rf_model", input_example=example)

        print(f"✅ Modèle sauvegardé dans MLflow ({_MLFLOW_EXPERIMENT})")
    except Exception as e:
        print(f"⚠️ Sauvegarde MLflow échouée ({e})")


def warmup(df: pd.DataFrame) -> None:
    """Pré-chauffe le cache ML au démarrage — sans aucune connexion réseau.

    Entraîne localement une fois, met en cache, puis lance la sauvegarde
    MLflow et la tentative de chargement du meilleur modèle en arrière-plan.
    """
    import threading
    global _CACHE
    if _CACHE is not None:
        return

    print("⏳ [ML] Entraînement local en cours…")
    city_clusters, rf, scaler, kmeans = _train_full_engine(df)
    _CACHE = {"city_clusters": city_clusters, "rf": rf}
    print("✅ [ML] Cache prêt.")

    # Tout ce qui touche MLflow se passe en arrière-plan, jamais dans le thread principal.
    def _mlflow_background():
        _log_to_mlflow(rf, scaler, kmeans, city_clusters)
        better = _try_load_from_mlflow(df)
        if better is not None:
            global _CACHE
            _CACHE = better
            print("✅ [ML] Meilleur modèle MLflow appliqué.")

    threading.Thread(target=_mlflow_background, daemon=True).start()


def engineer_features(df):
    """Ta fonction de nettoyage originale adaptée."""
    df = df.copy()
    cols_to_fix = ACTIVITY_FEATURES + ["temp_avg", "PIB par habitant (USD)"]
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def recommend(df, month, user_prefs, top_n=10, cluster_bonus_id=None):
    global _CACHE

    # Chargement lazy (une seule fois par process) — warmup() normalement appelé au démarrage.
    if _CACHE is None:
        warmup(df)

    rf_model = _CACHE["rf"]
    city_clusters = _CACHE["city_clusters"]

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
    # Pondération : température 25 %, activités 30 %, cluster IA 20 %,
    # infrastructure 4 × 5 % = 20 %.
    df_m["score"] = (
        (score_temp * 0.25)
        + (score_act * 0.30)
        + (score_ia * 0.20)
        + (score_electricite * 0.05)
        + (score_internet * 0.05)
        + (score_eau * 0.05)
        + (score_medecins * 0.05)
    )

    # Appliquer le budget comme multiplicateur (soft penalty)
    df_m["score"] = df_m["score"] * df_m["budget_match"]

    # Borner entre 0 et 1 puis convertir en pourcentage
    df_m["score"] = df_m["score"].clip(0, 1)
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
