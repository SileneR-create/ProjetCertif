"""
Tests des routes FastAPI — TravelMatch API
C12/C13 — Validation du contrat HTTP de chaque endpoint.

Les fonctions de base de données sont mockées pour isoler les tests
du moteur de persistance et les rendre exécutables sans Docker.
Le startup event est remplacé par une version allégée qui charge
des données de test sans toucher ni la DB ni MLflow.
"""

import os
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── DONNÉES DE TEST ───────────────────────────────────────────────────────────

def _make_fake_df():
    """Mini-dataset 10 villes × 12 mois pour les tests API."""
    cities = [
        "Paris", "Tokyo", "Nairobi", "New York", "Londres",
        "Bangkok", "Sydney", "Dubai", "Rome", "Berlin",
    ]
    rows = []
    for i, city in enumerate(cities):
        for month in range(1, 13):
            rows.append({
                "city": city,
                "month": month,
                "country": "France" if city == "Paris" else "World",
                "region": "Europe",
                "temp_avg": float(15 + i * 2),
                "nature": float(20 * (i % 5 + 1)),
                "patrimoine": float(20 * ((i + 1) % 5 + 1)),
                "culture": 60.0,
                "restaurant": 70.0,
                "nightlife": 50.0,
                "loisirs": 60.0,
                "Accès électricité (% pop)": 95.0,
                "Accès Internet (% pop)": 85.0,
                "Accès eau potable (% pop)": 90.0,
                "Médecins (pour 1000 habitants)": 2.5,
                "PIB par habitant (USD)": 40000.0,
                "Pauvreté < 3$/jour (% pop)": 1.0,
                "Revenu moyen par habitant ($/jour)": float(50 + i * 20),
                "Arrivées touristes internationaux (nb)": 1_000_000.0,
                "Recettes tourisme (USD)": 500_000_000.0,
                "valeur": 85.0,
                "budget_num": float(i + 1),
            })
    return pd.DataFrame(rows)


# ── FIXTURE CLIENT ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    TestClient avec startup simulée et dépendances de sécurité overridées.
    - Startup remplacée : pas de DB, pas de warmup ML
    - get_current_user remplacée : retourne un utilisateur fictif (id=1)
    - require_admin remplacée : retourne un admin fictif
    """
    import backend.app_api as app_module
    import recommender as rec_module
    from budget_categorizer import BudgetCategorizer
    from backend.security import get_current_user, require_admin

    fake_df = _make_fake_df()
    original_startup = list(app_module.app.router.on_startup)
    rec_module._CACHE = None

    def _test_startup():
        app_module.df_global = fake_df
        app_module.categorizer = BudgetCategorizer(fake_df, n_categories=4)

    app_module.app.router.on_startup = [_test_startup]

    # Bypass JWT : injecte un utilisateur fictif dans toutes les routes protégées
    fake_user = {"id": 1, "username": "test_user", "is_admin": 0}
    fake_admin = {"id": 1, "username": "test_admin", "is_admin": 1}
    app_module.app.dependency_overrides[get_current_user] = lambda: fake_user
    app_module.app.dependency_overrides[require_admin] = lambda: fake_admin

    with TestClient(app_module.app) as c:
        yield c

    app_module.app.router.on_startup = original_startup
    app_module.app.dependency_overrides = {}


# ── HEALTHCHECK ───────────────────────────────────────────────────────────────

def test_root_returns_online_status(client):
    """GET / doit retourner 200 et confirmer que l'API est en ligne."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


# ── AUTHENTIFICATION ──────────────────────────────────────────────────────────

_REGISTER_PAYLOAD = {
    "username": "alice_test",
    "email": "alice@test.com",
    "password": "SecurePass1",
    "interests": {
        "nature": 4, "culture": 3, "patrimoine": 2,
        "restaurant": 5, "nightlife": 1, "loisirs": 3,
    },
}


def test_register_success(client):
    """POST /auth/register avec données valides → 200 et message de succès."""
    with patch("backend.app_api.register_user", return_value={"success": True, "user_id": 42}):
        resp = client.post("/auth/register", json=_REGISTER_PAYLOAD)
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_register_duplicate_returns_400(client):
    """POST /auth/register avec username déjà pris → 400."""
    with patch("backend.app_api.register_user",
               return_value={"success": False, "error": "Nom d'utilisateur déjà pris."}):
        resp = client.post("/auth/register", json=_REGISTER_PAYLOAD)
    assert resp.status_code == 400


def test_login_success(client):
    """POST /auth/login avec identifiants valides → 200 avec objet user complet."""
    with patch("backend.app_api.login_user", return_value={
        "success": True,
        "user": {
            "id": 42, "username": "alice_test", "email": "alice@test.com",
            "created_at": "2025-01-01", "is_admin": 0,
        },
    }):
        resp = client.post("/auth/login", json={"username": "alice_test", "password": "SecurePass1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "alice_test"
    assert "id" in data["user"]


def test_login_wrong_password_returns_401(client):
    """POST /auth/login avec mauvais mot de passe → 401."""
    with patch("backend.app_api.login_user",
               return_value={"success": False, "error": "Mot de passe incorrect."}):
        resp = client.post("/auth/login", json={"username": "alice_test", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(client):
    """POST /auth/login avec utilisateur inconnu → 401."""
    with patch("backend.app_api.login_user",
               return_value={"success": False, "error": "Nom d'utilisateur introuvable."}):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


# ── BUDGET ────────────────────────────────────────────────────────────────────

def test_budget_info_returns_four_categories(client):
    """GET /budget/info doit retourner exactement 4 catégories de budget."""
    resp = client.get("/budget/info")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


# ── RECOMMANDATIONS ───────────────────────────────────────────────────────────

_RECO_PAYLOAD = {
    "month": 6,
    "user_id": 1,
    "top_n": 5,
    "prefs": {
        "temp_avg": 22,
        "nature": 4, "culture": 3, "patrimoine": 2,
        "restaurant": 5, "nightlife": 2, "loisirs": 3,
        "budget_label": "✈️ Moyen",
        "indice_electricite": 80,
        "indice_internet": 70,
        "indice_eau": 85,
        "indice_medecins": 2.0,
    },
}


def test_recommendations_returns_list(client):
    """POST /recommendations doit retourner une liste de destinations."""
    with patch("backend.app_api.get_user_interests", return_value={}), \
         patch("backend.app_api.save_search"):
        resp = client.post("/recommendations", json=_RECO_PAYLOAD)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert 1 <= len(results) <= _RECO_PAYLOAD["top_n"]


def test_recommendations_score_in_bounds(client):
    """C11 — Chaque score de matching doit être compris entre 0 et 100."""
    with patch("backend.app_api.get_user_interests", return_value={}), \
         patch("backend.app_api.save_search"):
        resp = client.post("/recommendations", json=_RECO_PAYLOAD)
    assert resp.status_code == 200
    for dest in resp.json():
        assert 0.0 <= dest["score_pct"] <= 100.0, (
            f"{dest['city']} a un score hors bornes : {dest['score_pct']}"
        )


def test_recommendations_contain_required_fields(client):
    """Chaque destination retournée doit avoir les champs attendus par le frontend."""
    with patch("backend.app_api.get_user_interests", return_value={}), \
         patch("backend.app_api.save_search"):
        resp = client.post("/recommendations", json=_RECO_PAYLOAD)
    assert resp.status_code == 200
    for dest in resp.json():
        for field in ("city", "score_pct", "cluster_label", "month"):
            assert field in dest, f"Champ '{field}' manquant pour '{dest.get('city', '?')}'"


def test_recommendations_filtered_by_month(client):
    """Les résultats ne doivent concerner que le mois demandé."""
    payload = {**_RECO_PAYLOAD, "month": 3}
    with patch("backend.app_api.get_user_interests", return_value={}), \
         patch("backend.app_api.save_search"):
        resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 200
    for dest in resp.json():
        assert dest["month"] == 3, (
            f"{dest['city']} retournée pour le mois {dest['month']} au lieu de 3"
        )


# ── FAVORIS ───────────────────────────────────────────────────────────────────

_FAV_PAYLOAD = {
    "user_id": 1,
    "city": "Paris",
    "country": "France",
    "month": 6,
    "score_pct": 87.5,
    "temp_avg": 22.0,
    "cluster_label": "🏛️ Patrimoine",
}

_FAKE_FAV = {
    "id": 1, "user_id": 1, "city": "Paris", "country": "France",
    "month": 6, "score_pct": 87.5, "temp_avg": 22.0,
    "cluster_label": "🏛️ Patrimoine", "saved_at": "2025-06-01",
}


def test_add_favorite_success(client):
    """POST /favorites doit ajouter un favori et retourner un message de succès."""
    with patch("backend.app_api.add_favorite", return_value={"success": True}):
        resp = client.post("/favorites", json=_FAV_PAYLOAD)
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_get_favorites_returns_list(client):
    """GET /favorites doit retourner la liste des favoris de l'utilisateur."""
    with patch("backend.app_api.get_favorites", return_value=[_FAKE_FAV]):
        resp = client.get("/favorites", params={"user_id": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["city"] == "Paris"


def test_check_favorite_is_true(client):
    """GET /favorites/check doit confirmer qu'un favori existe."""
    with patch("backend.app_api.is_favorite", return_value=True):
        resp = client.get("/favorites/check", params={"user_id": 1, "city": "Paris", "month": 6})
    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is True


def test_delete_favorite_success(client):
    """DELETE /favorites doit supprimer un favori et retourner un message de succès."""
    import json as _json
    with patch("backend.app_api.remove_favorite", return_value={"success": True}):
        resp = client.request(
            "DELETE", "/favorites",
            content=_json.dumps({"user_id": 1, "city": "Paris", "month": 6}),
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── HISTORIQUE ────────────────────────────────────────────────────────────────

def test_get_history_returns_list(client):
    """GET /history doit retourner l'historique de recherche de l'utilisateur."""
    fake_history = [{
        "id": 1, "month": 6,
        "preferences": {"temp_avg": 22},
        "top_result": "Paris",
        "searched_at": "2025-06-01T10:00:00",
    }]
    with patch("backend.app_api.get_search_history", return_value=fake_history):
        resp = client.get("/history", params={"user_id": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["top_result"] == "Paris"
