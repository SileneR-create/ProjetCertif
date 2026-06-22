from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, Optional, Any
from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
from prometheus_client import Gauge, Counter
import pandas as pd
import os
import sys

# Gestion du chemin pour les imports locaux
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Imports des modules metiers
from recommender import recommend, engineer_features, warmup  # noqa: E402
from backend.security import (  # noqa: E402
    create_access_token, get_current_user, require_admin, check_ownership,
)
from budget_categorizer import BudgetCategorizer  # noqa: E402
from backend.database import (  # noqa: E402
    init_db,
    add_favorite,
    remove_favorite,
    get_favorites,
    is_favorite,
    save_search,
    get_search_history,
    update_user_interests,
    get_user_interests,
    register_user,
    login_user,
    db_get_user_stats,
    db_get_all_users,
    db_delete_user,
    db_get_admin_search_history,
)

app = FastAPI(
    title="TravelMatch API", description="Backend de recommandation de destinations de voyage", version="1.0.0"
)
# ── EXPOSE LES MÉTRIQUES HTTP POUR PROMETHEUS ──
Instrumentator().instrument(app).expose(app)

# ── MÉTRIQUES MÉTIER DU MODÈLE IA ────────────────────────────────────────────
# Ces métriques permettent de détecter une dérive du modèle de recommandation
# (C11 — monitoring modèle, C20 — feedback loop MLOps).

METRIC_SCORE_MOYEN = Gauge(
    "travelmatch_score_moyen_matching",
    "Score moyen de matching (0-100) des recommandations retournées — signal de dérive du modèle",
)
METRIC_SCORE_MIN = Gauge(
    "travelmatch_score_min_matching",
    "Score minimum de matching parmi les recommandations retournées",
)
METRIC_RECOMMANDATIONS_TOTAL = Counter(
    "travelmatch_recommandations_total",
    "Nombre total d'appels à POST /recommendations",
)
METRIC_CLUSTER_DISTRIBUTION = Counter(
    "travelmatch_cluster_recommande_total",
    "Distribution des clusters recommandés (monitoring dérive archétypes)",
    ["cluster_label"],
)

df_global: pd.DataFrame = None
categorizer: BudgetCategorizer = None

_model_metrics: dict = {
    "recommandations_total": 0,
    "score_moyen": None,
    "score_min": None,
    "cluster_distribution": {},
}


@app.on_event("startup")
def startup_event():
    global df_global, categorizer
    init_db()

    print("✅ [STARTUP] Base de données initialisée (tables créées si manquantes).")

    DATA_PATH = os.path.join(ROOT_DIR, "DATA", "processed", "data_clean.csv")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Fichier introuvable : {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH)
    df_global = engineer_features(df_raw)
    categorizer = BudgetCategorizer(df_global, n_categories=4)

    print("🤖 [STARTUP] Pipeline de feature engineering appliquée avec succès.")

    # Pré-chauffe le cache ML : charge depuis MLflow ou entraîne une seule fois.
    # Les requêtes /recommendations suivantes ne déclencheront plus d'entraînement.
    try:
        warmup(df_global)
    except Exception as e:
        print(f"⚠️ [STARTUP] Pré-chauffe ML échouée ({e}) — le cache sera initialisé à la première requête.")


class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    interests: Dict[str, int]


class RecommendRequest(BaseModel):
    month: int
    user_id: int
    top_n: int = 10
    cluster_bonus: Optional[int] = None
    prefs: Dict[str, Any]


class FavoritePayload(BaseModel):
    user_id: int
    city: str
    country: Optional[str] = ""
    month: int
    score_pct: float
    temp_avg: float
    cluster_label: Optional[str] = ""


class FavoriteDeletePayload(BaseModel):
    user_id: int
    city: str
    month: int


# ═══════════════════════════════════════════════════════════
# CREATE  (POST)
# ═══════════════════════════════════════════════════════════


@app.post("/auth/register", tags=["Create"])
def api_register(user: UserRegister):
    result = register_user(user.username, user.email, user.password, user.interests)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "Utilisateur cree avec succes"}


@app.post("/auth/login", tags=["Create"])
def api_login(user: UserLogin):
    result = login_user(user.username, user.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    u = result["user"]
    token = create_access_token(u["id"], u["username"], u.get("is_admin", 0))
    return {"user": u, "access_token": token, "token_type": "bearer"}


@app.post("/recommendations", tags=["Create"])
def get_recommendations(req: RecommendRequest, current_user: dict = Depends(get_current_user)):
    if df_global is None:
        raise HTTPException(status_code=503, detail="Donnees non pretes")
    check_ownership(current_user, req.user_id)

    user_db_interests = get_user_interests(req.user_id)
    full_prefs = {**req.prefs, **user_db_interests}

    try:
        results_df = recommend(
            df_global,
            month=req.month,
            user_prefs=full_prefs,
            top_n=req.top_n,
            cluster_bonus_id=req.cluster_bonus,
        )
        if not results_df.empty:
            city_col = "city" if "city" in results_df.columns else results_df.columns[0]
            top_result = results_df.iloc[0][city_col]
            save_search(req.user_id, req.month, req.prefs, str(top_result))

            # ── Mise à jour des métriques modèle IA (feedback loop C11/C20) ──
            METRIC_RECOMMANDATIONS_TOTAL.inc()
            _model_metrics["recommandations_total"] += 1
            if "score_pct" in results_df.columns:
                score_moyen = float(results_df["score_pct"].mean())
                score_min = float(results_df["score_pct"].min())
                METRIC_SCORE_MOYEN.set(score_moyen)
                METRIC_SCORE_MIN.set(score_min)
                _model_metrics["score_moyen"] = round(score_moyen, 2)
                _model_metrics["score_min"] = round(score_min, 2)
            if "cluster_label" in results_df.columns:
                for label in results_df["cluster_label"].dropna():
                    METRIC_CLUSTER_DISTRIBUTION.labels(cluster_label=str(label)).inc()
                    _model_metrics["cluster_distribution"][str(label)] = (
                        _model_metrics["cluster_distribution"].get(str(label), 0) + 1
                    )

        return results_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/favorites", tags=["Create"])
def add_api_favorite(fav: FavoritePayload, current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, fav.user_id)
    try:
        add_favorite(fav.user_id, fav.city, fav.country, fav.month, fav.score_pct, fav.temp_avg, fav.cluster_label)
        return {"message": "Favori ajoute"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# READ  (GET)
# ═══════════════════════════════════════════════════════════


@app.get("/", tags=["Read"])
def read_root():
    return {"status": "online", "message": "Welcome to TravelMatch API"}


@app.get("/budget/info", tags=["Read"])
def get_budget_info():
    if categorizer is None:
        raise HTTPException(status_code=503, detail="Service indisponible")
    return categorizer.get_category_info()


@app.get("/budget/map-value", tags=["Read"])
def get_budget_map_value(label: str = Query(...)):
    if categorizer is None:
        return 1
    return categorizer.get_budget_map().get(label, 1)


@app.get("/users/{user_id}/interests", tags=["Read"])
def get_api_user_interests(user_id: int, current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, user_id)
    return get_user_interests(user_id)


@app.get("/favorites", tags=["Read"])
def get_api_favorites(user_id: int, current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, user_id)
    return get_favorites(user_id)


@app.get("/favorites/check", tags=["Read"])
def check_api_favorite(user_id: int, city: str, month: int,
                        current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, user_id)
    return {"is_favorite": is_favorite(user_id, city, month)}


@app.get("/history", tags=["Read"])
def get_api_history(user_id: int, limit: int = 15, current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, user_id)
    return get_search_history(user_id, limit=limit)


@app.get("/model/metrics", tags=["Read"])
def get_model_metrics(_: dict = Depends(require_admin)):
    """
    Retourne les métriques temps réel du modèle de recommandation IA.
    Permet de détecter une dérive de performance (monitoring C11/C20).
    """
    return {
        "recommandations_total": _model_metrics["recommandations_total"],
        "score_moyen_dernier_appel": _model_metrics["score_moyen"],
        "score_min_dernier_appel": _model_metrics["score_min"],
        "cluster_distribution_cumulee": _model_metrics["cluster_distribution"],
    }


@app.get("/api/admin/stats", tags=["Read"])
def admin_stats(_: dict = Depends(require_admin)):
    """Renvoie le nombre global d'utilisateurs et d'admins."""
    return db_get_user_stats()


@app.get("/api/admin/users", tags=["Read"])
def admin_users(_: dict = Depends(require_admin)):
    """Renvoie la liste complète des comptes utilisateurs."""
    return db_get_all_users()


@app.get("/api/admin/history", tags=["Read"])
def get_admin_history(_: dict = Depends(require_admin)):
    try:
        # 1. On récupère l'historique brut (qui contient les IDs ou les requêtes)
        results = db_get_admin_search_history()

        if not results:
            print("🚨 [DIAGNOSTIC] La table search_history est vide.")
            return []

        formatted_history = []
        for r in results:
            raw_query = r.get("query", "Inconnue")
            city_name = "Inconnue"

            # 2. TRADUCTION DE L'ID EN NOM DE VILLE VRAIE
            # Si le résultat brut est un ID numérique (ex: 5 ou "5")
            if str(raw_query).isdigit() and df_global is not None:
                city_id = int(raw_query)
                # On cherche la ligne correspondante dans le fichier des destinations
                # (Ajuste 'id' ou 'city' selon les colonnes réelles de ton df_global)
                city_row = df_global[df_global["id"] == city_id] if "id" in df_global.columns else pd.DataFrame()

                if not city_row.empty:
                    # On extrait le nom textuel de la ville
                    city_col = (
                        "city"
                        if "city" in df_global.columns
                        else ("ville" if "ville" in df_global.columns else df_global.columns[0])
                    )
                    city_name = str(city_row.iloc[0][city_col])
                else:
                    city_name = f"Destination n°{city_id}"
            else:
                # Si ce n'était pas un ID mais déjà du texte, on le garde tel quel
                city_name = str(raw_query)

            # 3. Envoi du dictionnaire propre au frontend
            formatted_history.append(
                {
                    "username": r.get("username", "Anonyme"),
                    "searched_at": r.get("searched_at", "Pas de date"),
                    "city": city_name,  # 👈 Contient maintenant le vrai nom ("Tokyo", "Paris"...) !
                    "month": str(r.get("month", "N/A")),
                    "query": "Filtres appliqués",
                }
            )

        print(f"✅ [DIAGNOSTIC] {len(formatted_history)} lignes traduites envoyées au panneau Admin.")
        return formatted_history

    except Exception as e:
        print(f"❌ [DIAGNOSTIC] Erreur lors de la traduction des IDs villes : {str(e)}")
        return []


@app.get("/api/admin/favorites/top", tags=["Read"])
def admin_top_favorites(_: dict = Depends(require_admin)):
    """Récupère le décompte global de toutes les villes mises en favoris."""
    from backend.database import get_session, Favorite

    session = get_session()
    try:
        from sqlalchemy import func

        # Compte le nombre de fois que chaque ville apparaît dans la table favorites
        rows = (
            session.query(Favorite.city, func.count(Favorite.id).label("total"))
            .group_by(Favorite.city)
            .order_by(func.count(Favorite.id).desc())
            .limit(10)
            .all()
        )
        return [{"city": r.city, "count": r.total} for r in rows]
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════
# UPDATE  (PUT)
# ═══════════════════════════════════════════════════════════


@app.put("/users/{user_id}/interests", tags=["Update"])
def update_api_user_interests(user_id: int, interests: Dict[str, int],
                               current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, user_id)
    try:
        update_user_interests(user_id, interests)
        return {"message": "Centres d'interet mis a jour"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# DELETE  (DELETE)
# ═══════════════════════════════════════════════════════════


@app.delete("/favorites", tags=["Delete"])
def remove_api_favorite(fav: FavoriteDeletePayload, current_user: dict = Depends(get_current_user)):
    check_ownership(current_user, fav.user_id)
    try:
        remove_favorite(fav.user_id, fav.city, fav.month)
        return {"message": "Favori retire"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/users/{user_id}", tags=["Delete"])
def admin_delete(user_id: int, _: dict = Depends(require_admin)):
    """Supprime un compte utilisateur."""
    success = db_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression.")
    return {"status": "success", "message": "Utilisateur supprime."}
