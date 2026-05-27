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

# Imports de vos modules métiers existants
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

# ── INITIALISATION FASTAPI ──
app = FastAPI(
    title="TravelMatch API",
    description="Backend de recommandation de destinations de voyage et gestion utilisateur",
    version="1.0.0",
)

# Variables globales chargées au démarrage
df_global: pd.DataFrame = None
categorizer: BudgetCategorizer = None


@app.on_event("startup")
def startup_event():
    """Initialisation au démarrage de l'API (Base de données et Données CSV)"""
    global df_global, categorizer

    # 1. Initialisation SQLite
    init_db()

    # 2. Chargement et feature engineering des données voyages
    DATA_PATH = os.path.join(ROOT_DIR, "DATA", "processed", "data_clean.csv")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Le fichier de données est introuvable à l'emplacement : {DATA_PATH}")

    df_raw = pd.read_csv(DATA_PATH)
    df_global = engineer_features(df_raw)

    # 3. Entraînement/Initialisation du BudgetCategorizer
    categorizer = BudgetCategorizer(df_global, n_categories=4)


# ── MODÈLES DE DONNÉES (PYDANTIC) ──


class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    interests: Dict[str, int] = Field(..., description="Dictionnaire des intérêts de 1 à 5")


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


# ── ENDPOINTS ──


@app.get("/", tags=["General"])
def read_root():
    return {"status": "online", "message": "Welcome to TravelMatch API ✈️"}


# ── DEPT: AUTHENTIFICATION & UTILISATEURS ──


@app.post("/auth/register", tags=["Authentication"])
def api_register(user: UserRegister):
    result = register_user(user.username, user.email, user.password, user.interests)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return {"message": "Utilisateur créé avec succès"}


@app.post("/auth/login", tags=["Authentication"])
def api_login(user: UserLogin):
    result = login_user(user.username, user.password)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["error"])
    return {"user": result["user"]}


@app.get("/users/{user_id}/interests", tags=["Users"])
def get_api_user_interests(user_id: int):
    interests = get_user_interests(user_id)
    return interests


@app.put("/users/{user_id}/interests", tags=["Users"])
def update_api_user_interests(user_id: int, interests: Dict[str, int]):
    try:
        update_user_interests(user_id, interests)
        return {"message": "Centres d'intérêt mis à jour"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DEPT: BUDGET ──


@app.get("/budget/info", tags=["Budget"])
def get_budget_info():
    """Renvoie les tranches budgétaires calculées par le BudgetCategorizer"""
    if categorizer is None:
        raise HTTPException(status_code=503, detail="Service de catégorisation indisponible")
    return categorizer.get_category_stats()


@app.get("/budget/map-value", tags=["Budget"])
def get_budget_map_value(label: str = Query(..., description="Label de la catégorie budgétaire")):
    """Associe un label budgétaire à sa valeur numérique brute"""
    if categorizer is None:
        return 1
    return categorizer.budget_map.get(label, 1)


# ── DEPT: MOTEUR DE RECOMMANDATION ──


@app.post("/recommendations", tags=["Recommendation"])
def get_recommendations(req: RecommendRequest):
    """Calcule le classement des destinations et enregistre la recherche dans l'historique"""
    global df_global
    if df_global is None:
        raise HTTPException(status_code=503, detail="Données non prêtes")

    # 1. Récupération des intérêts profonds de l'utilisateur depuis la DB SQLite
    user_db_interests = get_user_interests(req.user_id)

    # 2. Fusion des curseurs (sidebar) et du profil utilisateur
    full_prefs = {**req.prefs, **user_db_interests}

    try:
        # 3. Calcul via la fonction originelle de recommender.py
        results_df = recommend(
            df_global,
            month=req.month,
            user_prefs=full_prefs,
            top_n=req.top_n,
            cluster_bonus_id=req.cluster_bonus,
        )

        # 4. Enregistrement asynchrone de la recherche dans l'historique de la DB
        if not results_df.empty:
            city_col = "Ville" if "Ville" in results_df.columns else results_df.columns[0]
            top_result = results_df.iloc[0][city_col]
            save_search(req.user_id, req.month, req.prefs, str(top_result))

        # 5. Conversion du DataFrame Pandas en JSON sérialisable
        return results_df.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du moteur : {str(e)}")


# ── DEPT: FAVORIS & HISTORIQUE ──


@app.get("/favorites", tags=["Favorites"])
def get_api_favorites(user_id: int):
    return get_favorites(user_id)


@app.get("/favorites/check", tags=["Favorites"])
def check_api_favorite(user_id: int, city: str, month: int):
    is_fav = is_favorite(user_id, city, month)
    return {"is_favorite": is_fav}


@app.post("/favorites", tags=["Favorites"])
def add_api_favorite(fav: FavoritePayload):
    try:
        add_favorite(fav.user_id, fav.city, fav.country, fav.month, fav.score_pct, fav.temp_avg, fav.cluster_label)
        return {"message": f"{fav.city} ajouté aux favoris"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/favorites", tags=["Favorites"])
def remove_api_favorite(fav: FavoriteDeletePayload):
    try:
        remove_favorite(fav.user_id, fav.city, fav.month)
        return {"message": f"{fav.city} retiré des favoris"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", tags=["History"])
def get_api_history(user_id: int, limit: int = 15):
    return get_search_history(user_id, limit=limit)
