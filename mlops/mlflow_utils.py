"""Helpers MLflow pour le suivi d'expériences (entraînement de modèles).

Centralise la configuration du tracking et la journalisation des artefacts
graphiques (courbes, matrices) et des métriques, pour les deux familles
d'expériences du projet :

  * classification  : learning curve, classification report, confusion matrix,
    importances de variables ;
  * clustering      : courbes de sélection (elbow / silhouette /
    Davies-Bouldin / Calinski-Harabasz) et diagramme de silhouette.

Toute la logique de plotting est headless (backend Agg) afin d'être rejouable
en CI sans serveur graphique.
"""

import os
import shutil
import tempfile

import matplotlib

matplotlib.use("Agg")  # backend sans affichage (CI-friendly)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import mlflow  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay,
    roc_curve,
    auc,
    silhouette_score,
    silhouette_samples,
    davies_bouldin_score,
    calinski_harabasz_score,
)
from sklearn.model_selection import learning_curve  # noqa: E402
from sklearn.preprocessing import label_binarize  # noqa: E402


# ─────────────────────────────────────────────────────────
#  CONFIGURATION DU TRACKING
# ─────────────────────────────────────────────────────────


def setup_mlflow(experiment_name: str) -> None:
    """Configure l'URI de tracking et sélectionne l'expérience.

    Priorité : variable d'environnement ``MLFLOW_TRACKING_URI`` > serveur local
    ``http://localhost:5000``. Si le serveur est injoignable, bascule
    automatiquement sur un store SQLite local ``sqlite:///mlflow.db`` (le file
    store ``./mlruns`` est déprécié par MLflow) pour que l'entraînement
    aboutisse quand même.
    """
    uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    try:
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(experiment_name)
        print(f"✅ MLflow tracking : {uri} | experiment={experiment_name}")
    except Exception as e:  # serveur éteint, réseau, etc.
        local = "sqlite:///" + os.path.abspath("./mlflow.db").replace("\\", "/")
        mlflow.set_tracking_uri(local)
        mlflow.set_experiment(experiment_name)
        print(f"⚠️ Serveur MLflow injoignable ({e}).\n   → Bascule locale : {local}")


def _log_figure(fig, filename: str, artifact_path: str = "plots") -> None:
    """Sauvegarde une figure matplotlib et l'envoie à MLflow comme artefact."""
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, filename)
        fig.savefig(path, bbox_inches="tight", dpi=120)
        mlflow.log_artifact(path, artifact_path=artifact_path)
    finally:
        plt.close(fig)
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────
#  ARTEFACTS — CLASSIFICATION
# ─────────────────────────────────────────────────────────


def log_classification_report(y_true, y_pred, filename: str = "classification_report.txt") -> dict:
    """Logge le rapport de classification (texte) et les métriques agrégées."""
    text = classification_report(y_true, y_pred, zero_division=0)
    report = classification_report(y_true, y_pred, zero_division=0, output_dict=True)

    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        mlflow.log_artifact(path, artifact_path="reports")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if "accuracy" in report:
        mlflow.log_metric("accuracy", float(report["accuracy"]))
    for avg in ("macro avg", "weighted avg"):
        if avg in report:
            tag = avg.replace(" avg", "")
            mlflow.log_metric(f"{tag}_precision", float(report[avg]["precision"]))
            mlflow.log_metric(f"{tag}_recall", float(report[avg]["recall"]))
            mlflow.log_metric(f"{tag}_f1", float(report[avg]["f1-score"]))
    return report


def log_confusion_matrix(y_true, y_pred, labels=None, filename: str = "confusion_matrix.png"):
    """Trace et logge la matrice de confusion."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    fig, ax = plt.subplots(figsize=(7, 6))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Matrice de confusion")
    _log_figure(fig, filename)
    return cm


def log_learning_curve(estimator, X, y, cv: int = 5, scoring: str = "f1_weighted",
                       filename: str = "learning_curve.png") -> None:
    """Trace et logge la learning curve (train vs validation croisée)."""
    sizes, train_scores, val_scores = learning_curve(
        estimator, X, y, cv=cv, scoring=scoring,
        train_sizes=np.linspace(0.1, 1.0, 6), n_jobs=-1,
        shuffle=True, random_state=42,
    )
    tr_m, tr_s = train_scores.mean(axis=1), train_scores.std(axis=1)
    va_m, va_s = val_scores.mean(axis=1), val_scores.std(axis=1)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, tr_m, "o-", label="Entraînement")
    ax.fill_between(sizes, tr_m - tr_s, tr_m + tr_s, alpha=0.15)
    ax.plot(sizes, va_m, "o-", label="Validation (CV)")
    ax.fill_between(sizes, va_m - va_s, va_m + va_s, alpha=0.15)
    ax.set_xlabel("Taille du jeu d'entraînement")
    ax.set_ylabel(f"Score ({scoring})")
    ax.set_title("Learning curve")
    ax.legend()
    ax.grid(alpha=0.3)
    _log_figure(fig, filename)


def log_feature_importances(model, feature_names, filename: str = "feature_importances.png") -> None:
    """Trace et logge l'importance des variables (si le modèle l'expose)."""
    if not hasattr(model, "feature_importances_"):
        return
    imp = model.feature_importances_
    order = np.argsort(imp)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([feature_names[i] for i in order], imp[order])
    ax.set_title("Importance des variables")
    ax.set_ylabel("Importance")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _log_figure(fig, filename)
    for i in order:
        mlflow.log_metric(f"importance_{feature_names[i]}", float(imp[i]))


def log_classification_report_heatmap(y_true, y_pred,
                                       filename: str = "classification_report_heatmap.png") -> None:
    """Heatmap visuelle du rapport de classification (précision / rappel / F1 par classe)."""
    report = classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    classes = [k for k in report if k not in ("accuracy", "macro avg", "weighted avg")]
    metrics = ["precision", "recall", "f1-score"]
    labels = ["Précision", "Rappel", "F1-score"]

    data = np.array([[report[c][m] for m in metrics] for c in classes])

    fig, ax = plt.subplots(figsize=(7, max(4, 0.5 * len(classes) + 2)))
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(labels)
    ax.set_yticks(range(len(classes)))
    ax.set_yticklabels([f"Cluster {c}" for c in classes])
    for i in range(len(classes)):
        for j in range(len(metrics)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Rapport de classification — Heatmap")
    _log_figure(fig, filename, artifact_path="reports")


def log_roc_curves(model, X_test, y_test, filename: str = "roc_curves.png") -> None:
    """Courbes ROC one-vs-rest pour chaque classe + AUC loggé comme métrique."""
    if not hasattr(model, "predict_proba"):
        return

    classes = sorted(np.unique(y_test))
    y_bin = label_binarize(y_test, classes=classes)
    y_score = model.predict_proba(X_test)

    fig, ax = plt.subplots(figsize=(8, 6))
    auc_values = []
    for i, cls in enumerate(classes):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_score[:, i])
        roc_auc = auc(fpr, tpr)
        auc_values.append(roc_auc)
        ax.plot(fpr, tpr, label=f"Cluster {cls} (AUC = {roc_auc:.2f})")
        mlflow.log_metric(f"auc_cluster_{cls}", roc_auc)

    macro_auc = float(np.mean(auc_values))
    mlflow.log_metric("macro_auc", macro_auc)

    ax.plot([0, 1], [0, 1], "k--", label="Aléatoire")
    ax.set_xlabel("Taux de faux positifs")
    ax.set_ylabel("Taux de vrais positifs")
    ax.set_title(f"Courbes ROC — One-vs-Rest (macro AUC = {macro_auc:.2f})")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    _log_figure(fig, filename)


def log_cv_scores_distribution(cv_results: dict, scoring: str = "f1_weighted",
                                filename: str = "cv_scores_distribution.png") -> None:
    """Boxplot de la distribution des scores par fold pour le meilleur candidat."""
    split_keys = sorted(k for k in cv_results if k.startswith("split") and k.endswith("test_score"))
    if not split_keys:
        return

    best_idx = int(np.argmax(cv_results["mean_test_score"]))
    scores = [float(cv_results[k][best_idx]) for k in split_keys]
    mean_s = float(np.mean(scores))
    std_s = float(np.std(scores))

    fig, ax = plt.subplots(figsize=(6, 4))
    bp = ax.boxplot(scores, patch_artist=True, widths=0.4)
    bp["boxes"][0].set_facecolor("#a8d8ea")
    ax.scatter([1] * len(scores), scores, color="steelblue", zorder=5, s=40)
    ax.axhline(mean_s, color="red", linestyle="--", label=f"Moyenne = {mean_s:.3f} ± {std_s:.3f}")
    ax.set_xticks([1])
    ax.set_xticklabels([scoring])
    ax.set_ylabel("Score")
    ax.set_title(f"Distribution des scores CV ({len(scores)} folds) — meilleur candidat")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    _log_figure(fig, filename)


# ─────────────────────────────────────────────────────────
#  ARTEFACTS — CLUSTERING
# ─────────────────────────────────────────────────────────


def compute_clustering_metrics(X, labels) -> dict:
    """Indices de qualité d'un partitionnement (hors inertie, propre à KMeans).

    - silhouette         : ∈ [-1, 1], plus haut = mieux ;
    - davies_bouldin     : ≥ 0, plus bas = mieux ;
    - calinski_harabasz  : ≥ 0, plus haut = mieux.
    """
    return {
        "silhouette": float(silhouette_score(X, labels)),
        "davies_bouldin": float(davies_bouldin_score(X, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
    }


def log_cluster_selection_curves(k_values, inertias, silhouettes, davies_bouldin, calinski,
                                 filename: str = "cluster_selection_curves.png") -> None:
    """Trace les 4 courbes de sélection du nombre de clusters sur une planche."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    panels = [
        (axes[0, 0], inertias, "Méthode du coude (elbow)", "Inertie (↓)"),
        (axes[0, 1], silhouettes, "Score de silhouette", "Silhouette (↑)"),
        (axes[1, 0], davies_bouldin, "Indice de Davies-Bouldin", "Davies-Bouldin (↓)"),
        (axes[1, 1], calinski, "Indice de Calinski-Harabasz", "Calinski-Harabasz (↑)"),
    ]
    for ax, values, title, ylabel in panels:
        ax.plot(k_values, values, "o-")
        ax.set_title(title)
        ax.set_xlabel("Nombre de clusters k")
        ax.set_ylabel(ylabel)
        ax.set_xticks(list(k_values))
        ax.grid(alpha=0.3)
    fig.suptitle("Sélection du nombre de clusters (KMeans)", fontsize=14)
    _log_figure(fig, filename)


def log_silhouette_diagram(X, labels, k: int, filename: str = "silhouette_diagram.png") -> None:
    """Trace le diagramme de silhouette par cluster pour le modèle retenu."""
    sample_sil = silhouette_samples(X, labels)
    avg = silhouette_score(X, labels)

    fig, ax = plt.subplots(figsize=(8, 6))
    y_lower = 10
    for i in range(k):
        vals = np.sort(sample_sil[labels == i])
        size = len(vals)
        y_upper = y_lower + size
        ax.fill_betweenx(np.arange(y_lower, y_upper), 0, vals, alpha=0.7)
        ax.text(-0.04, y_lower + size / 2, str(i))
        y_lower = y_upper + 10
    ax.axvline(avg, color="red", linestyle="--", label=f"silhouette moyenne = {avg:.3f}")
    ax.set_title(f"Diagramme de silhouette (k={k})")
    ax.set_xlabel("Coefficient de silhouette")
    ax.set_ylabel("Échantillons regroupés par cluster")
    ax.set_yticks([])
    ax.legend(loc="best")
    _log_figure(fig, filename)


# ─────────────────────────────────────────────────────────
#  ARTEFACTS — BENCHMARK
# ─────────────────────────────────────────────────────────


def log_table(df: pd.DataFrame, filename: str = "table.csv", artifact_path: str = "reports") -> None:
    """Logge un DataFrame en CSV + version texte lisible."""
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, filename)
        df.to_csv(csv_path)
        mlflow.log_artifact(csv_path, artifact_path=artifact_path)
        txt_path = os.path.join(tmp, filename.replace(".csv", ".txt"))
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(df.to_string())
        mlflow.log_artifact(txt_path, artifact_path=artifact_path)


# ─────────────────────────────────────────────────────────
#  ARTEFACTS — PROFILAGE DES CLUSTERS (explicabilité)
# ─────────────────────────────────────────────────────────


def log_cluster_activity_heatmap(cluster_means: pd.DataFrame,
                                 filename: str = "cluster_activity_heatmap.png",
                                 vmin: float = 1, vmax: float = 5) -> None:
    """Heatmap clusters × activités (moyenne, échelle d'origine) = l'ADN lisible."""
    data = cluster_means.values
    fig, ax = plt.subplots(figsize=(1.0 * data.shape[1] + 3, 0.6 * data.shape[0] + 2.5))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels(cluster_means.columns, rotation=40, ha="right")
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(cluster_means.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", fontsize=8)
    ax.set_title("ADN d'activités par cluster (moyenne, échelle 1–5)")
    fig.colorbar(im, ax=ax, shrink=0.7)
    _log_figure(fig, filename)


def log_cluster_sizes(sizes: dict, filename: str = "cluster_sizes.png") -> None:
    """Diagramme des tailles de clusters (nb de villes)."""
    keys = [str(k) for k in sizes]
    vals = list(sizes.values())
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(keys, vals)
    ax.set_title("Taille des clusters")
    ax.set_xlabel("cluster")
    ax.set_ylabel("nb de villes")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, str(v), ha="center", fontsize=9)
    _log_figure(fig, filename)


def log_pca_scatter(X_scaled, labels, filename: str = "pca_scatter.png") -> None:
    """Projection PCA 2D des destinations, colorée par cluster."""
    from sklearn.decomposition import PCA

    pcs = PCA(n_components=2, random_state=42).fit_transform(X_scaled)
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(pcs[:, 0], pcs[:, 1], c=labels, cmap="tab10", s=18, alpha=0.8)
    ax.set_xlabel("Composante principale 1")
    ax.set_ylabel("Composante principale 2")
    ax.set_title("Projection PCA des destinations (couleur = cluster)")
    ax.add_artist(ax.legend(*scatter.legend_elements(), title="cluster", loc="best", fontsize=8))
    ax.grid(alpha=0.3)
    _log_figure(fig, filename)


def log_model_comparison(scores: dict, metric_name: str = "test f1_weighted",
                         filename: str = "model_comparison.png") -> None:
    """Trace un comparatif (barres) des modèles du benchmark."""
    names = list(scores.keys())
    values = [scores[n] for n in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, values)
    ax.set_title("Benchmark des classifieurs")
    ax.set_ylabel(metric_name)
    ax.set_ylim(0, 1.05)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01, f"{val:.3f}", ha="center")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    ax.grid(axis="y", alpha=0.3)
    _log_figure(fig, filename)
