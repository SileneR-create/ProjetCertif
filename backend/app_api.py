from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional, Any
from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
import pandas as pd
import os
import sys

# Gestion du chemin pour les imports locaux
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Imports des modules metiers
from recommender import recommend, engineer_features  # noqa: E402
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
# ── EXPOSE LES MÉTRIQUES POUR PROMETHEUS ──
Instrumentator().instrument(app).expose(app)

df_global: pd.DataFrame = None
categorizer: BudgetCategorizer = None


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


@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to TravelMatch API"}


@app.post("/auth/register")
def api_register(user: UserRegister):
    result = register_user(user.username, user.email, user.password, user.interests)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "Utilisateur cree avec succes"}


@app.post("/auth/login")
def api_login(user: UserLogin):
    result = login_user(user.username, user.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return {"user": result["user"]}


@app.get("/users/{user_id}/interests")
def get_api_user_interests(user_id: int):
    return get_user_interests(user_id)


@app.put("/users/{user_id}/interests")
def update_api_user_interests(user_id: int, interests: Dict[str, int]):
    try:
        update_user_interests(user_id, interests)
        return {"message": "Centres d'interet mis a jour"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budget/info")
def get_budget_info():
    if categorizer is None:
        raise HTTPException(status_code=503, detail="Service indisponible")
    return categorizer.get_category_info()


@app.get("/budget/map-value")
def get_budget_map_value(label: str = Query(...)):
    if categorizer is None:
        return 1
    return categorizer.get_budget_map.get(label, 1)


@app.post("/recommendations")
def get_recommendations(req: RecommendRequest):
    if df_global is None:
        raise HTTPException(status_code=503, detail="Donnees non pretes")

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
        return results_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/favorites")
def get_api_favorites(user_id: int):
    return get_favorites(user_id)


@app.get("/favorites/check")
def check_api_favorite(user_id: int, city: str, month: int):
    return {"is_favorite": is_favorite(user_id, city, month)}


@app.post("/favorites")
def add_api_favorite(fav: FavoritePayload):
    try:
        add_favorite(fav.user_id, fav.city, fav.country, fav.month, fav.score_pct, fav.temp_avg, fav.cluster_label)
        return {"message": "Favori ajoute"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/favorites")
def remove_api_favorite(fav: FavoriteDeletePayload):
    try:
        remove_favorite(fav.user_id, fav.city, fav.month)
        return {"message": "Favori retire"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def get_api_history(user_id: int, limit: int = 15):
    return get_search_history(user_id, limit=limit)


# ─────────────────────────────────────────────────────────
# ➕ NOUVELLES ROUTES POUR LE PANNEAU D'ADMINISTRATION
# ─────────────────────────────────────────────────────────


@app.get("/api/admin/stats")
def admin_stats():
    """Renvoie le nombre global d'utilisateurs et d'admins."""
    return db_get_user_stats()


@app.get("/api/admin/users")
def admin_users():
    """Renvoie la liste complète des comptes utilisateurs."""
    return db_get_all_users()


@app.delete("/api/admin/users/{user_id}")
def admin_delete(user_id: int):
    """Supprime un compte utilisateur."""
    success = db_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression.")
    return {"status": "success", "message": "Utilisateur supprime."}


@app.get("/api/admin/history")
def get_admin_history():
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


@app.get("/api/admin/favorites/top")
def admin_top_favorites():
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
