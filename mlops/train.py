"""Pipeline d'entraînement et de suivi MLflow pour TravelMatch.

Le VRAI rôle de MLflow : tracer l'itération et la comparaison des modèles
(hyperparamètres, métriques, artefacts, modèle versionné) — pas l'inférence.

Deux expériences distinctes :

  * ``TravelMatch_Clustering``  — sélection du nombre de clusters k de KMeans.
    Un run imbriqué par valeur de k, avec inertie + silhouette + Davies-Bouldin
    + Calinski-Harabasz, puis courbes de sélection et diagramme de silhouette
    sur le run parent, et enfin le modèle KMeans retenu.

  * ``TravelMatch_Classifier``  — RandomizedSearchCV sur un RandomForest qui
    apprend à mapper un vecteur de préférences → archétype de destination
    (les labels KMeans). C'est un modèle « surrogate » : ses métriques de
    classification mesurent surtout la séparabilité des clusters. On logge la
    learning curve, le classification report, la matrice de confusion, les
    importances de variables, les meilleurs hyperparamètres et le modèle.

Usage :
    python -m mlops.train --task all
    python -m mlops.train --task clustering --k-min 2 --k-max 12
    python -m mlops.train --task classification --best-k 6 --n-iter 30

Pré-requis : le serveur MLflow (docker-compose) sur http://localhost:5000,
sinon le script bascule sur un store local ./mlruns.
"""

import os
import sys
import argparse

import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from scipy.stats import randint, uniform, loguniform
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split

# Modèles optionnels : inclus dans le benchmark uniquement s'ils sont installés
try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False
try:
    from lightgbm import LGBMClassifier
    _HAS_LGBM = True
except ImportError:
    _HAS_LGBM = False

# Imports locaux (racine du projet sur le path)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from mlops.features import build_destination_features, ACTIVITY_FEATURES, RAW_PATH as DATA_PATH  # noqa: E402
from mlops import mlflow_utils as mu  # noqa: E402


# ─────────────────────────────────────────────────────────
#  EXPÉRIENCE 1 — CLUSTERING (sélection de k + profilage)
# ─────────────────────────────────────────────────────────


def profile_clusters(cities, X_raw, descriptive, labels, centers_scaled, X_scaled, top_n_cities=4):
    """Construit le profil explicable de chaque cluster.

    Retourne (cluster_means, summary) où :
      * ``cluster_means`` = moyenne des 9 activités par cluster (échelle 1–5) ;
      * ``summary``       = label auto (top-2 activités distinctives), taille,
        budget moyen, température moyenne, région dominante et villes
        représentatives (les plus proches du centroïde).
    """
    df = X_raw.copy()
    df["cluster"] = labels
    means = df.groupby("cluster")[ACTIVITY_FEATURES].mean()

    # Distinctivité : z-score des moyennes entre clusters → top-2 activités
    z = (means - means.mean()) / means.std(ddof=0).replace(0, 1)
    auto_labels = {c: " + ".join(z.loc[c].sort_values(ascending=False).head(2).index) for c in means.index}

    desc = descriptive.copy()
    desc["cluster"] = labels
    budget_mean = desc.groupby("cluster")["budget_num"].mean()
    temp_mean = desc.groupby("cluster")["temp_annual_avg"].mean()
    region_top = desc.groupby("cluster")["region"].agg(lambda s: s.value_counts().idxmax())
    sizes = pd.Series(labels).value_counts().sort_index()

    reps = {}
    for c in means.index:
        idx = np.where(labels == c)[0]
        dist = np.linalg.norm(X_scaled[idx] - centers_scaled[c], axis=1)
        nearest = idx[np.argsort(dist)[:top_n_cities]]
        reps[c] = ", ".join(cities.iloc[nearest]["city"].astype(str).tolist())

    summary = pd.DataFrame({
        "label": auto_labels,
        "n_villes": sizes,
        "budget_moyen_1a3": budget_mean.round(2),
        "temp_moy_annuelle": temp_mean.round(1),
        "region_dominante": region_top,
        "villes_representatives": reps,
    })
    summary.index.name = "cluster"
    return means, summary


def run_clustering(k_min: int = 2, k_max: int = 12, final_k: int = None) -> int:
    mu.setup_mlflow("TravelMatch_Clustering")
    cities, X_raw, descriptive = build_destination_features()
    X = StandardScaler().fit_transform(X_raw)  # standardisation des 9 activités
    k_values = list(range(k_min, k_max + 1))

    inertias, silhouettes, davies, calinski = [], [], [], []

    with mlflow.start_run(run_name="kmeans_selection"):
        mlflow.log_param("k_min", k_min)
        mlflow.log_param("k_max", k_max)
        mlflow.log_param("n_cities", len(cities))
        mlflow.log_param("n_features", len(ACTIVITY_FEATURES))
        mlflow.log_param("features", ",".join(ACTIVITY_FEATURES))
        mlflow.log_param("scaler", "StandardScaler")

        for k in k_values:
            with mlflow.start_run(run_name=f"k={k}", nested=True):
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(X)
                metrics = mu.compute_clustering_metrics(X, labels)

                mlflow.log_param("k", k)
                mlflow.log_metric("inertia", float(km.inertia_))
                for name, val in metrics.items():
                    mlflow.log_metric(name, val)

                inertias.append(float(km.inertia_))
                silhouettes.append(metrics["silhouette"])
                davies.append(metrics["davies_bouldin"])
                calinski.append(metrics["calinski_harabasz"])
                print(f"k={k:2d} | silhouette={metrics['silhouette']:.3f} "
                      f"| DB={metrics['davies_bouldin']:.3f} "
                      f"| CH={metrics['calinski_harabasz']:.0f}")

        # Courbes de sélection sur le run parent
        mu.log_cluster_selection_curves(k_values, inertias, silhouettes, davies, calinski)

        # La silhouette informe, le métier décide : sur des données d'activités
        # continues, les métriques internes favorisent peu de clusters (souvent k=2).
        # Pour des archétypes actionnables, on autorise un k « métier » (final_k).
        best_k_metric = int(k_values[int(np.argmax(silhouettes))])
        mlflow.log_metric("best_k_silhouette", best_k_metric)
        chosen_k = int(final_k) if final_k else best_k_metric
        mlflow.log_param("chosen_k", chosen_k)
        mlflow.log_param("k_selection", "business_override" if final_k else "silhouette_max")
        print(f"\nMeilleur k (silhouette) = {best_k_metric} | k retenu pour le profilage = {chosen_k}")

        # Modèle final + diagramme de silhouette
        final = KMeans(n_clusters=chosen_k, random_state=42, n_init=10)
        final_labels = final.fit_predict(X)
        mu.log_silhouette_diagram(X, final_labels, chosen_k)

        # ── PROFILAGE EXPLICABLE DES CLUSTERS ──
        means, summary = profile_clusters(
            cities, X_raw, descriptive, final_labels, final.cluster_centers_, X
        )
        named_means = means.rename(index={c: f"C{c} · {summary.loc[c, 'label']}" for c in means.index})
        mu.log_cluster_activity_heatmap(named_means)
        mu.log_cluster_sizes(summary["n_villes"].to_dict())
        mu.log_pca_scatter(X, final_labels)
        mu.log_table(summary, filename="cluster_profiles.csv")

        for c in summary.index:
            mlflow.log_param(f"cluster_{c}", summary.loc[c, "label"])
            mlflow.log_metric(f"cluster_{c}_size", int(summary.loc[c, "n_villes"]))
        _safe_log_model(final, "kmeans_final", X_raw)  # best-effort (robuste aux écarts de version serveur)

        print("\nProfil des clusters :")
        print(summary.to_string())

    return chosen_k


# ─────────────────────────────────────────────────────────
#  EXPÉRIENCE 2 — CLASSIFICATION (benchmark multi-modèles)
# ─────────────────────────────────────────────────────────


def build_candidates() -> dict:
    """Classifieurs candidats du benchmark.

    Chaque entrée = (estimateur, distribution d'hyperparamètres préfixée
    ``clf__`` car l'estimateur est inséré dans une Pipeline avec le scaler).
    XGBoost / LightGBM ne sont inclus que s'ils sont installés.
    """
    candidates = {
        "logreg": (
            LogisticRegression(max_iter=2000),
            {"clf__C": loguniform(1e-2, 1e2)},
        ),
        "random_forest": (
            RandomForestClassifier(random_state=42),
            {
                "clf__n_estimators": randint(50, 400),
                "clf__max_depth": randint(3, 25),
                "clf__min_samples_split": randint(2, 12),
                "clf__min_samples_leaf": randint(1, 8),
                "clf__max_features": ["sqrt", "log2", None],
            },
        ),
        "gradient_boosting": (
            GradientBoostingClassifier(random_state=42),
            {
                "clf__n_estimators": randint(50, 300),
                "clf__max_depth": randint(2, 6),
                "clf__learning_rate": loguniform(1e-2, 3e-1),
            },
        ),
    }
    if _HAS_XGB:
        candidates["xgboost"] = (
            XGBClassifier(random_state=42, eval_metric="mlogloss", tree_method="hist"),
            {
                "clf__n_estimators": randint(50, 400),
                "clf__max_depth": randint(2, 8),
                "clf__learning_rate": loguniform(1e-2, 3e-1),
                "clf__subsample": uniform(0.6, 0.4),
                "clf__colsample_bytree": uniform(0.6, 0.4),
            },
        )
    if _HAS_LGBM:
        candidates["lightgbm"] = (
            LGBMClassifier(random_state=42, verbose=-1),
            {
                "clf__n_estimators": randint(50, 400),
                "clf__max_depth": randint(2, 12),
                "clf__learning_rate": loguniform(1e-2, 3e-1),
                "clf__num_leaves": randint(15, 63),
            },
        )
    return candidates


def _safe_log_model(model, name: str, input_example) -> None:
    """Enregistre un modèle dans MLflow sans faire échouer le run en cas de souci.

    Certains flavors (XGBoost/LightGBM dans une Pipeline) peuvent être refusés par
    la garde de sérialisation de MLflow ; on journalise alors un tag plutôt que de
    perdre les métriques du benchmark.
    """
    try:
        mlflow.sklearn.log_model(model, name=name, input_example=input_example.head(3))
    except Exception as e:
        mlflow.set_tag("model_logged", "false")
        print(f"   ({name} : métriques OK, modèle non enregistré → {str(e).splitlines()[0][:90]})")


def run_classification(best_k: int = 6, n_iter: int = 30, models=None) -> None:
    mu.setup_mlflow("TravelMatch_Classifier")
    cities, X, descriptive = build_destination_features()  # 560 villes, 9 activités (brutes)
    X_scaled = StandardScaler().fit_transform(X)

    # Cibles = archétypes définis par KMeans → modèle surrogate.
    # LabelEncoder garantit des labels denses 0..K-1 (requis par XGBoost).
    y = LabelEncoder().fit_transform(KMeans(n_clusters=best_k, random_state=42, n_init=10).fit_predict(X_scaled))
    # X = features BRUTES : la normalisation est faite DANS la pipeline (évite la fuite de données)

    # CV adaptative : certains clusters peuvent être minuscules (voire singletons)
    # quand best_k est élevé. On adapte le nombre de folds et on retombe sur une CV
    # non stratifiée si une classe a trop peu de membres pour être stratifiée.
    counts = pd.Series(y).value_counts()
    min_count = int(counts.min())
    n_splits = int(max(2, min(5, min_count)))
    if min_count >= n_splits:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        stratify = y
    else:
        from sklearn.model_selection import KFold
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        stratify = None
        print(f"⚠️ Classe la plus rare = {min_count} membre(s) → CV non stratifiée, {n_splits} folds. "
              f"Signe que k={best_k} produit des clusters déséquilibrés.")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=stratify)

    candidates = build_candidates()
    if models:
        candidates = {k: v for k, v in candidates.items() if k in models}

    comparison = {}                       # nom -> f1 test (pour le graphe comparatif)
    best_overall = (None, None, -1.0)     # (nom, estimateur, f1_test)

    with mlflow.start_run(run_name="classifier_benchmark"):
        mlflow.log_param("strategy", "RandomizedSearchCV")
        mlflow.log_param("best_k", best_k)
        mlflow.log_param("n_iter", n_iter)
        mlflow.log_param("cv_folds", n_splits)
        mlflow.log_param("scoring", "f1_weighted")
        mlflow.log_param("candidates", ",".join(candidates))
        mlflow.log_metric("min_class_size", min_count)

        for name, (estimator, param_dist) in candidates.items():
            with mlflow.start_run(run_name=name, nested=True):
                mlflow.log_param("model", name)
                try:
                    pipe = Pipeline([("scaler", StandardScaler()), ("clf", estimator)])
                    search = RandomizedSearchCV(
                        pipe, param_distributions=param_dist, n_iter=n_iter,
                        cv=cv, scoring="f1_weighted", random_state=42, n_jobs=-1, refit=True,
                    )
                    search.fit(X_tr, y_tr)
                    best = search.best_estimator_

                    # Évaluation test + artefacts
                    y_pred = best.predict(X_te)
                    report = mu.log_classification_report(y_te, y_pred)
                    test_f1 = float(report["weighted avg"]["f1-score"])

                    for p, v in search.best_params_.items():
                        mlflow.log_param(p, v)
                    mlflow.log_metric("cv_best_f1_weighted", float(search.best_score_))
                    mlflow.log_metric("test_f1_weighted", test_f1)
                    if hasattr(search, "refit_time_"):
                        mlflow.log_metric("refit_time_sec", float(search.refit_time_))

                    mu.log_confusion_matrix(y_te, y_pred, labels=sorted(np.unique(y)))
                    mu.log_learning_curve(best, X, y, cv=cv, scoring="f1_weighted")
                    mu.log_feature_importances(best.named_steps["clf"], list(ACTIVITY_FEATURES))

                    comparison[name] = test_f1
                    print(f"{name:18s} | CV f1={search.best_score_:.3f} | test f1={test_f1:.3f}")
                    if test_f1 > best_overall[2]:
                        best_overall = (name, best, test_f1)

                    # Enregistrement du modèle en best-effort : un échec d'enregistrement
                    # (ex: garde 'untrusted types' MLflow sur les flavors XGB/LGBM) ne doit
                    # PAS invalider les métriques déjà calculées.
                    _safe_log_model(best, name, X_te)
                except Exception as e:
                    # Vrai échec d'entraînement (ex: classes non contiguës sur clusters
                    # singletons) : on marque le run et on continue le benchmark.
                    mlflow.set_tag("status", "failed")
                    mlflow.log_param("error", str(e).splitlines()[0][:240])
                    print(f"{name:18s} | ÉCHEC : {str(e).splitlines()[-1][:110]}")

        # Synthèse comparative sur le run parent (uniquement les modèles aboutis)
        if comparison:
            mu.log_model_comparison(comparison)
            for n, v in comparison.items():
                mlflow.log_metric(f"{n}_test_f1", v)
        if best_overall[1] is not None:
            mlflow.log_param("best_model", best_overall[0])
            mlflow.log_metric("best_test_f1", best_overall[2])
            _safe_log_model(best_overall[1], "best_model", X_te)
            print(f"\n🏆 Meilleur modèle : {best_overall[0]} (test f1 = {best_overall[2]:.3f})")


# ─────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Entraînement + suivi MLflow TravelMatch")
    parser.add_argument("--task", choices=["clustering", "classification", "all"], default="all")
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=12)
    parser.add_argument("--final-k", type=int, default=None,
                        help="k « métier » retenu pour le profilage (sinon meilleur silhouette).")
    parser.add_argument("--best-k", type=int, default=None,
                        help="k pour la classification (sinon repris du clustering ou 6).")
    parser.add_argument("--n-iter", type=int, default=30, help="Itérations RandomizedSearchCV.")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Sous-ensemble de modèles (ex: --models logreg random_forest xgboost).")
    args = parser.parse_args()

    best_k = args.best_k
    if args.task in ("clustering", "all"):
        best_k = run_clustering(args.k_min, args.k_max, final_k=args.final_k)
    if args.task in ("classification", "all"):
        run_classification(best_k=best_k if best_k is not None else 6,
                           n_iter=args.n_iter, models=args.models)


if __name__ == "__main__":
    main()
