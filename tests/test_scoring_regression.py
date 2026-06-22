"""
Tests de régression du moteur de scoring — TravelMatch
C11 — Surveillance du modèle : invariants mathématiques et sensibilité.

Vérifie que les règles de scoring du moteur de recommandation
sont stables et cohérentes sur des données de test contrôlées,
indépendamment des données de production.

Dataset de test : 6 villes avec profils d'activité quasi-identiques,
divisées en 2 groupes de température (≈20°C vs ≈50°C), ce qui permet
d'isoler et de tester chaque composante du score.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import recommender


# ── DATASET CONTRÔLÉ ──────────────────────────────────────────────────────────

def _make_scoring_dataset() -> pd.DataFrame:
    """
    6 villes × 12 mois avec :
    - 3 villes "fraiches" (temp ≈ 20°C) et 3 villes "chaudes" (temp ≈ 50°C)
    - Profils d'activité quasi-identiques (variation de 0.5 par ville)
      pour que KMeans obtienne des centroïdes distincts sans fausser
      la comparaison température.
    """
    cities = [
        ("Fraiche_A", 20.0), ("Fraiche_B", 22.0), ("Fraiche_C", 24.0),
        ("Chaude_A",  48.0), ("Chaude_B",  50.0), ("Chaude_C",  52.0),
    ]
    rows = []
    for i, (city, temp) in enumerate(cities):
        for month in range(1, 13):
            rows.append({
                "city": city,
                "month": month,
                "country": "TestLand",
                "region": "TestRegion",
                "temp_avg": temp,
                "nature":      60.0 + i * 0.5,
                "patrimoine":  60.0 + i * 0.5,
                "culture":     60.0 + i * 0.5,
                "restaurant":  60.0 + i * 0.5,
                "nightlife":   60.0 + i * 0.5,
                "loisirs":     60.0 + i * 0.5,
                "Accès électricité (% pop)": 95.0,
                "Accès Internet (% pop)": 85.0,
                "Accès eau potable (% pop)": 90.0,
                "Médecins (pour 1000 habitants)": 2.5,
                "PIB par habitant (USD)": 40000.0,
                "Pauvreté < 3$/jour (% pop)": 1.0,
                "Revenu moyen par habitant ($/jour)": 60.0,
                "Arrivées touristes internationaux (nb)": 1_000_000.0,
                "Recettes tourisme (USD)": 500_000_000.0,
                "valeur": 85.0,
                "budget_num": 2.0,
            })
    return pd.DataFrame(rows)


_SCORING_DF = _make_scoring_dataset()

_BASE_PREFS = {
    "temp_avg": 20,
    "nature": 3, "patrimoine": 3, "culture": 3,
    "restaurant": 3, "nightlife": 3, "loisirs": 3,
    "indice_electricite": 80,
    "indice_internet": 70,
    "indice_eau": 85,
    "indice_medecins": 2.0,
}


# ── FIXTURE ISOLATION ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_ml_cache():
    """Réinitialise le cache ML avant chaque test pour garantir l'isolation."""
    recommender._CACHE = None
    yield
    recommender._CACHE = None


# ── INVARIANTS MATHÉMATIQUES ──────────────────────────────────────────────────

def test_score_always_between_0_and_100():
    """C11 — Les scores de matching doivent toujours être dans [0, 100]."""
    results = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=6)
    assert not results.empty, "Aucun résultat retourné."
    out_of_bounds = results[~results["score_pct"].between(0.0, 100.0)]
    assert out_of_bounds.empty, (
        f"Scores hors bornes détectés :\n{out_of_bounds[['city', 'score_pct']]}"
    )


def test_results_sorted_by_score_descending():
    """Les résultats doivent être triés par score décroissant."""
    results = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=6)
    scores = results["score_pct"].tolist()
    assert scores == sorted(scores, reverse=True), (
        f"Résultats non triés par score décroissant : {scores}"
    )


def test_top_n_is_respected():
    """Le nombre de résultats ne doit jamais dépasser top_n."""
    for top_n in (1, 3, 6):
        recommender._CACHE = None
        results = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=top_n)
        assert len(results) <= top_n, (
            f"top_n={top_n} demandé, {len(results)} résultats retournés."
        )


def test_scoring_is_deterministic():
    """C11 — Même requête → mêmes résultats (reproductibilité du modèle)."""
    r1 = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=6)
    r2 = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=6)
    assert list(r1["city"]) == list(r2["city"]), "Classement non déterministe entre deux appels."
    assert list(r1["score_pct"]) == list(r2["score_pct"]), "Scores non déterministes."


def test_required_output_fields_present():
    """Chaque résultat doit contenir les champs attendus par le frontend."""
    results = recommender.recommend(_SCORING_DF, month=6, user_prefs=_BASE_PREFS, top_n=3)
    required = {"city", "score_pct", "cluster_id", "cluster_label", "month"}
    for _, row in results.iterrows():
        missing = required - set(row.index)
        assert not missing, f"Champs manquants pour '{row['city']}' : {missing}"


# ── SENSIBILITÉ TEMPÉRATURE ───────────────────────────────────────────────────

def test_cool_cities_score_higher_for_cool_preference():
    """
    C11 — Sensibilité température : pour un utilisateur préférant 20°C,
    les villes fraiches (≈20°C) doivent obtenir un score moyen supérieur
    aux villes chaudes (≈50°C), même en tenant compte du bonus de cluster.

    Justification mathématique :
    - temp_diff fraiches ≤ 5°C  → score_temp = 1.0  (poids 25 %)
    - temp_diff chaudes  ≥ 28°C → score_temp = 0.0  (poids 25 %)
    - Écart température = 0.25, supérieur au poids cluster (0.20),
      garantissant que la température domine le classement.
    """
    results = recommender.recommend(
        _SCORING_DF, month=6, user_prefs={**_BASE_PREFS, "temp_avg": 20}, top_n=6,
    )

    cool = {"Fraiche_A", "Fraiche_B", "Fraiche_C"}
    hot  = {"Chaude_A",  "Chaude_B",  "Chaude_C"}

    cool_scores = results[results["city"].isin(cool)]["score_pct"]
    hot_scores  = results[results["city"].isin(hot)]["score_pct"]

    assert not cool_scores.empty, "Aucune ville fraiche dans les résultats."
    assert not hot_scores.empty,  "Aucune ville chaude dans les résultats."

    cool_avg = cool_scores.mean()
    hot_avg  = hot_scores.mean()

    assert cool_avg > hot_avg, (
        f"Score moyen villes fraiches ({cool_avg:.1f}) ≤ villes chaudes ({hot_avg:.1f}). "
        "La pondération température (25 %) ne fonctionne pas correctement."
    )


# ── TEST DE SEUIL DU MODÈLE (C12) ────────────────────────────────────────────

def test_model_performance_threshold():
    """
    C12 — Le Random Forest doit atteindre un F1 pondéré >= 0.65 sur le jeu de
    test (25 % des données, test_size=0.25, random_state=42).

    Ce test réentraîne le modèle sur le vrai dataset (DATA/raw/) pour vérifier
    que les performances restent au-dessus du seuil acceptable après chaque
    modification du code ou des données.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.cluster import KMeans
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import f1_score

    from mlops.features import build_destination_features

    SEUIL_F1 = 0.65

    # 1. Charger les features réelles
    cities, X, descriptive = build_destination_features()
    X_arr = X.values

    # 2. Produire les labels via KMeans (même pipeline que train.py)
    kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
    y = kmeans.fit_predict(X_arr)

    # 3. Découpage 75 / 25 (identique à train.py ligne 288)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_arr, y, test_size=0.25, random_state=42
    )

    # 4. Entraînement Random Forest avec pipeline de normalisation
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
    ])
    pipe.fit(X_tr, y_tr)

    # 5. Évaluation
    y_pred = pipe.predict(X_te)
    f1 = f1_score(y_te, y_pred, average="weighted")

    assert f1 >= SEUIL_F1, (
        f"F1 pondéré = {f1:.3f} < seuil {SEUIL_F1}. "
        "Le modèle Random Forest ne respecte pas le seuil de performance minimal."
    )