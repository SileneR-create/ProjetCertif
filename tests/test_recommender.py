import pytest
import pandas as pd
import numpy as np
from recommender import train_ml_engine, recommend, engineer_features

@pytest.fixture
def fake_travel_dataset():
    """Génère un mini-dataset propre pour valider les règles mathématiques de l'IA."""
    cities = ["Paris", "Tokyo", "Nairobi", "New York", "Londres", "Reunion"]
    data = []
    # Création de données stables pour 6 villes sur le mois 1 (Janvier)
    for i, city in enumerate(cities):
        data.append({
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
            "valeur": 85
        })
    return pd.DataFrame(data)

def test_ml_engine_clustering(fake_travel_dataset):
    """Règle : Le modèle doit catégoriser les destinations sans planter."""
    city_clusters, rf_model = train_ml_engine(fake_travel_dataset)
    
    assert not city_clusters.empty
    assert "cluster_id" in city_clusters.columns
    # Le modèle RandomForest doit être capable de prédire
    assert hasattr(rf_model, "predict")

def test_recommendation_logic(fake_travel_dataset):
    """Règle : Les scores calculés doivent être cohérents (bornés entre 0 et 100)."""
    user_prefs = {
        "temp_avg": 25,
        "budget_label": "✈️ Moyen",
        "nature": 3,
        "culture": 4
    }
    
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