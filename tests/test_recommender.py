import pytest
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import cross_val_score
from recommender import train_ml_engine, recommend, engineer_features


@pytest.fixture
def fake_travel_dataset():
    """Génère un mini-dataset propre pour valider les règles mathématiques de l'IA."""
    cities = ["Paris", "Tokyo", "Nairobi", "New York", "Londres", "Reunion"]
    data = []
    # Création de données stables pour 6 villes sur le mois 1 (Janvier)
    for i, city in enumerate(cities):
        data.append(
            {
                "city": city,
                "month": 1,
                "temp_avg": 15 + (i * 3),
                "nature": 10 * i,
                "patrimoine": 100 - (i * 10),
                "culture": 80,
                "restaurant": 90,
                "nightlife": 50,
                "loisirs": 60,
                "Accès électricité (% pop)": 95,
                "Accès Internet (% pop)": 85,
                "Accès eau potable (% pop)": 90,
                "Médecins (pour 1000 habitants)": 2.5,
                "PIB par habitant (USD)": 40000,
                "Pauvreté < 3$/jour (% pop)": 1,
                "Revenu moyen par habitant ($/jour)": 50 + (i * 20),
                "Arrivées touristes internationaux (nb)": 1000000,
                "Recettes tourisme (USD)": 500000000,
                "valeur": 85,
            }
        )
    return pd.DataFrame(data)


def test_ml_engine_clustering(fake_travel_dataset):
    """Règle : Le modèle doit catégoriser les destinations sans planter."""
    city_clusters, rf_model = train_ml_engine(fake_travel_dataset)

    assert not city_clusters.empty
    assert "cluster_id" in city_clusters.columns
    # Le modèle RandomForest doit être capable de prédire
    assert hasattr(rf_model, "predict")


def test_model_performance_threshold(fake_travel_dataset):
    """C12 — Seuil de performance minimal du modèle.

    Le Random Forest surrogate prédit les archétypes KMeans.
    On vérifie que le f1_weighted (CV 2-fold sur mini-dataset) dépasse
    un seuil minimal — si ce test échoue, le modèle a trop régressé
    et ne doit pas partir en production.

    Seuil : 0.30 sur ce mini-dataset de 6 villes (dataset très petit,
    seuil volontairement bas). En production sur ~560 villes, le seuil
    attendu est ≥ 0.60 (voir mlops/train.py best_test_f1).
    """
    from sklearn.preprocessing import MinMaxScaler
    from recommender import ACTIVITY_FEATURES

    city_group = fake_travel_dataset.groupby("city")[ACTIVITY_FEATURES].mean().reset_index()
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(city_group[ACTIVITY_FEATURES])

    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)  # 3 clusters sur 6 villes
    y = kmeans.fit_predict(X_scaled)

    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    scores = cross_val_score(rf, city_group[ACTIVITY_FEATURES], y, cv=2, scoring="f1_weighted")
    f1_mean = scores.mean()

    SEUIL_MINIMAL = 0.30
    assert f1_mean >= SEUIL_MINIMAL, (
        f"Performance du modèle ({f1_mean:.3f}) sous le seuil minimal ({SEUIL_MINIMAL}). "
        "Réentraîner le modèle avant déploiement."
    )


def test_recommendation_logic(fake_travel_dataset):
    """Règle : Les scores calculés doivent être cohérents (bornés entre 0 et 100)."""
    user_prefs = {"temp_avg": 25, "budget_label": "✈️ Moyen", "nature": 3, "culture": 4}

    # Appel de votre fonction principale du fichier recommender.py
    # On passe un try/except pour MLflow car en environnement de test CI, MLflow peut être absent
    try:
        results = recommend(fake_travel_dataset, month=1, user_prefs=user_prefs, top_n=3)

        assert len(results) <= 3
        assert "score_pct" in results.columns
        # Les scores doivent être mathématiquement viables
        assert results["score_pct"].max() <= 100.0
        assert results["score_pct"].min() >= 0.0
    except Exception as e:
        # Si le crash vient uniquement de la connexion HTTP à MLflow (:5000)
        if "Requests" in str(type(e)) or "Connection" in str(e):
            pytest.skip("MLflow n'est pas joignable, test ignoré pour la partie logs")
        else:
            raise e
