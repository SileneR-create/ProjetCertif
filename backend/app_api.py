from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import pandas as pd
import os
import sys

# Gestion du chemin pour les imports locaux
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Imports des modules metiers
from recommender import recommend, engineer_features, ACTIVITY_FEATURES
from budget_categorizer import BudgetCategorizer
from backend.database import (
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
)

app = FastAPI(
    title="TravelMatch API", description="Backend de recommandation de destinations de voyage", version="1.0.0"
)

df_global: pd.DataFrame = None
categorizer: BudgetCategorizer = None


@app.on_event("startup")
def startup_event():
    global df_global, categorizer
    init_db()
    DATA_PATH = os.path.join(ROOT_DIR, "DATA", "processed", "data_clean.csv")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Fichier introuvable : {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH)
    df_global = engineer_features(df_raw)
    categorizer = BudgetCategorizer(df_global, n_categories=4)


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
        raise HTTPException(status_code=41, detail=result["error"])
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
    return categorizer.get_category_stats()


@app.get("/budget/map-value")
def get_budget_map_value(label: str = Query(...)):
    if categorizer is None:
        return 1
    return categorizer.budget_map.get(label, 1)


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
            city_col = "Ville" if "Ville" in results_df.columns else results_df.columns[0]
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
