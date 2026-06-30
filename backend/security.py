"""
Sécurité de l'API TravelMatch — JWT Bearer Token.

Deux niveaux d'accès :
  - Utilisateur authentifié  → get_current_user
  - Administrateur seulement → require_admin

check_ownership() empêche un utilisateur d'accéder aux données d'un autre.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("SECRET_KEY", "travelmatch-dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

_http_bearer = HTTPBearer(auto_error=True)


def create_access_token(user_id: int, username: str, is_admin: int) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError
        return {
            "id": int(user_id),
            "username": payload.get("username"),
            "is_admin": int(payload.get("is_admin", 0)),
        }
    except (InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return current_user


def check_ownership(current_user: dict, user_id: int) -> None:
    """Lève 403 si l'utilisateur accède aux données d'un autre (sauf admin)."""
    if current_user["id"] != user_id and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé : vous ne pouvez accéder qu'à vos propres données.",
        )
