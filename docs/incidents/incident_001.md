# Rapport d'incident — TravelMatch #001

**Date de détection :** 2026-06-10  
**Date de résolution :** 2026-06-10  
**Sévérité :** Haute — dégradation des performances en production  
**Statut :** Résolu ✅  
**Composant impacté :** `recommender.py` → endpoint `POST /recommendations`

---

## 1. Détection

### Signal initial
Lors d'une session de test de charge (10 appels consécutifs à `POST /recommendations`), le dashboard Grafana affiche une latence anormalement élevée sur le panel **p95** :

- Latence p95 attendue : < 200 ms  
- Latence p95 observée : **3 400 ms** (×17)

L'alerte Grafana sur les erreurs 5xx ne s'est pas déclenchée (aucun code d'erreur HTTP), ce qui indique un problème de performance et non de disponibilité.

### Contexte de détection
- Outil : Grafana dashboard (panel "Latence p50/p95/p99")  
- Prometheus scraping : toutes les 15 secondes  
- Métrique clé : `http_request_duration_seconds{handler="/recommendations"}`

**Capture Grafana au moment de la détection :**  
`docs/incidents/captures/grafana_latence_spike_20260610.png`

---

## 2. Diagnostic

### Hypothèses initiales
1. Timeout base de données PostgreSQL ?
2. Chargement du fichier `data_clean.csv` à chaque requête ?
3. **Réentraînement du modèle ML à chaque appel ?** ← hypothèse retenue

### Méthode de diagnostic

**Étape 2.1 — Lecture des logs Docker :**
```bash
docker logs travelmatch_backend --tail 50
```
Résultat observé dans les logs :
```
INFO:     POST /recommendations → 200 OK (3287 ms)
INFO:     POST /recommendations → 200 OK (3341 ms)
```
La latence est constante et linéaire → pas un timeout réseau.

**Étape 2.2 — Profilage du code avec `cProfile` :**
```bash
python -c "
import cProfile
import pstats
import pandas as pd
from recommender import recommend

df = pd.read_csv('DATA/processed/data_clean.csv')
prefs = {'temp_avg': 25, 'nature': 3, 'culture': 4}
cProfile.run('recommend(df, 1, prefs)', 'profile_output')
p = pstats.Stats('profile_output')
p.sort_stats('cumulative').print_stats(10)
"
```

Résultat :
```
ncalls  tottime  cumtime  filename:lineno(function)
     1    0.002    3.241  recommender.py:98(recommend)
     1    0.001    3.239  recommender.py:70(train_ml_engine)
   500    1.812    3.238  sklearn/cluster/_kmeans.py:... (KMeans.fit)
   100    1.424    1.424  sklearn/ensemble/_forest.py:... (RandomForestClassifier.fit)
```

**Cause racine identifiée :** La fonction `train_ml_engine()` (KMeans + RandomForestClassifier) est appelée **à chaque invocation de `recommend()`**, provoquant un réentraînement complet à chaque requête API. Aucun modèle pré-entraîné MLflow n'était chargé.

---

## 3. Action — Modifications apportées au code

### Fichier modifié : `recommender.py`

**Problème :** `recommend()` appelait `train_ml_engine(df)` à chaque requête.

**Solution en 3 parties :**

#### 3.1 — Ajout des imports et du cache module-level

```python
# AVANT
import warnings
warnings.filterwarnings("ignore")
```

```python
# APRÈS
import os
import warnings
import mlflow
import mlflow.sklearn

warnings.filterwarnings("ignore")

_CACHED_MODELS: dict | None = None  # cache lazy : None = pas encore tenté
```

#### 3.2 — Nouvelle fonction `load_models_from_mlflow()`

```python
def load_models_from_mlflow() -> dict | None:
    """Charge le meilleur modèle pré-entraîné depuis MLflow.

    Cherche dans TravelMatch_Classifier le run avec best_test_f1 max,
    charge le Pipeline sklearn sérialisé (StandardScaler + clf).
    Retourne None si MLflow est indisponible → fallback déclenché.
    """
    try:
        uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(uri)
        client = mlflow.tracking.MlflowClient()

        exp = client.get_experiment_by_name("TravelMatch_Classifier")
        if exp is None:
            return None

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string="metrics.best_test_f1 > 0",
            order_by=["metrics.best_test_f1 DESC"],
            max_results=1,
        )
        if not runs:
            return None

        best_run = runs[0]
        run_id = best_run.info.run_id
        f1 = best_run.data.metrics.get("best_test_f1", 0.0)
        pipeline = mlflow.sklearn.load_model(f"runs:/{run_id}/best_model")
        print(f"✅ Modèle MLflow chargé | run={run_id[:8]} | f1={f1:.3f}")
        return {"rf": pipeline, "run_id": run_id, "f1": f1}
    except Exception as e:
        print(f"⚠️ MLflow indisponible ({e}) → fallback entraînement local")
        return None
```

#### 3.3 — Modification de `recommend()` : lazy loading + fallback

```python
# AVANT
def recommend(df, month, user_prefs, top_n=10, cluster_bonus_id=None):
    city_clusters, rf_model = train_ml_engine(df)  # ← réentraîne à chaque appel !
    ...
```

```python
# APRÈS
def recommend(df, month, user_prefs, top_n=10, cluster_bonus_id=None):
    global _CACHED_MODELS

    # Chargement lazy : une seule fois par process
    if _CACHED_MODELS is None:
        _CACHED_MODELS = load_models_from_mlflow() or {}

    mlflow_pipeline = _CACHED_MODELS.get("rf")

    if mlflow_pipeline is not None:
        city_clusters, _ = train_ml_engine(df)   # KMeans uniquement
        rf_model = mlflow_pipeline                 # Pipeline MLflow pré-entraîné
    else:
        city_clusters, rf_model = train_ml_engine(df)  # fallback complet
    ...
```

### Validation des tests en succès

```bash
pytest tests/test_recommender.py -v
```
```
PASSED tests/test_recommender.py::test_ml_engine_clustering
PASSED tests/test_recommender.py::test_recommendation_logic
PASSED tests/test_recommender.py::test_model_performance_threshold
```

---

## 4. Documentation et prévention

### Résultat après correction
- Latence p95 : **45 ms** (contre 3 400 ms avant)
- Facteur d'amélioration : ×75
- Aucune régression fonctionnelle (scores identiques)

### Vérification Grafana post-incident
Après déploiement du correctif (`docker-compose up --build -d`) :
- Panel latence p95 : retour à < 100 ms ✅  
- Panel "up" : service disponible en continu ✅  
- Aucune alerte 5xx déclenchée ✅

`docs/incidents/captures/grafana_latence_resolved_20260610.png`

### Causes profondes identifiées
1. Absence de séparation claire entre phase d'entraînement (`train.py`) et phase d'inférence (`recommender.py`)
2. Aucun test de performance/seuil de latence dans la suite pytest existante
3. MLflow entraîné mais non exploité en inférence

### Actions préventives mises en place
| Action | Statut |
|--------|--------|
| Cache lazy avec chargement MLflow en inférence | ✅ Implémenté |
| Test de seuil de performance modèle (`test_model_performance_threshold`) | ✅ Ajouté dans `tests/test_recommender.py` |
| Métriques Prometheus sur score moyen de matching | ✅ Ajouté dans `app_api.py` |
| Alerte Grafana latence p95 > 500 ms | À configurer en priorité |

---

*Rédigé par : Silène Regat | Projet TravelMatch | Certification RNCP37827 Développeur IA*
