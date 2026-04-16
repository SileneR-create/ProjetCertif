import json
import hashlib
import secrets
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float,
    Text, ForeignKey, UniqueConstraint)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from scripts.DB_CONFIG import DB_CONFIG

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# database.py — version SQLAlchemy (PostgreSQL)


# ─── CONFIG ─────────────────────────────────────────────

DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/travelmatch"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


# ─── MODELS ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    is_admin = Column(Integer, default=0)


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    city = Column(String, nullable=False)
    country = Column(String)
    month = Column(Integer, nullable=False)
    score_pct = Column(Float)
    temp_avg = Column(Float)
    cluster_label = Column(String)
    saved_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "city", "month"),
    )


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(Integer, nullable=False)
    preferences = Column(Text, nullable=False)
    top_result = Column(Text)
    searched_at = Column(String, nullable=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    preferences = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name"),
    )


class UserInterests(Base):
    __tablename__ = "user_interests"

    user_id = Column(Integer, primary_key=True)
    interests = Column(Text, nullable=False)
    updated_at = Column(String, nullable=False)


# ─── INIT DB ────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)


# ─── HELPERS ────────────────────────────────────────────

def get_session():
    return SessionLocal()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


# ─── AUTH ───────────────────────────────────────────────


def login_user(username, password):
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username.strip()).first()

        if not user:
            return {"success": False, "error": "Nom d'utilisateur introuvable."}

        if _hash_password(password, user.salt) != user.password:
            return {"success": False, "error": "Mot de passe incorrect."}

        return {"success": True, "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at,
            "is_admin": user.is_admin
        }}

    finally:
        session.close()


# ─── PROFILES ───────────────────────────────────────────

def save_profile(user_id: int, name: str, preferences: dict):
    session = get_session()
    try:
        now = datetime.now().isoformat()
        profile = session.query(Profile).filter_by(
            user_id=user_id,
            name=name.strip()
        ).first()

        if profile:
            profile.preferences = json.dumps(preferences)
            profile.updated_at = now
        else:
            profile = Profile(
                user_id=user_id,
                name=name.strip(),
                preferences=json.dumps(preferences),
                created_at=now,
                updated_at=now
            )
            session.add(profile)

        session.commit()
        return {"success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}

    finally:
        session.close()


def get_profiles(user_id: int):
    session = get_session()
    try:
        profiles = session.query(Profile).filter_by(user_id=user_id).order_by(Profile.updated_at.desc()).all()

        return [
            {
                "id": p.id,
                "user_id": p.user_id,
                "name": p.name,
                "preferences": json.loads(p.preferences),
                "created_at": p.created_at,
                "updated_at": p.updated_at
            }
            for p in profiles
        ]

    finally:
        session.close()


def delete_profile(profile_id: int, user_id: int):
    session = get_session()
    try:
        session.query(Profile).filter_by(id=profile_id, user_id=user_id).delete()
        session.commit()
        return {"success": True}
    finally:
        session.close()


# ─── FAVORITES ──────────────────────────────────────────

def add_favorite(user_id, city, country, month, score_pct, temp_avg, cluster_label):
    session = get_session()
    try:
        fav = session.query(Favorite).filter_by(
            user_id=user_id, city=city, month=month
        ).first()

        now = datetime.now().isoformat()

        if fav:
            fav.country = country
            fav.score_pct = score_pct
            fav.temp_avg = temp_avg
            fav.cluster_label = cluster_label
            fav.saved_at = now
        else:
            fav = Favorite(
                user_id=user_id,
                city=city,
                country=country,
                month=month,
                score_pct=score_pct,
                temp_avg=temp_avg,
                cluster_label=cluster_label,
                saved_at=now
            )
            session.add(fav)

        session.commit()
        return {"success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}

    finally:
        session.close()


def remove_favorite(user_id, city, month):
    session = get_session()
    try:
        session.query(Favorite).filter_by(
            user_id=user_id, city=city, month=month
        ).delete()
        session.commit()
        return {"success": True}
    finally:
        session.close()


def get_favorites(user_id):
    session = get_session()
    try:
        favs = session.query(Favorite).filter_by(user_id=user_id).order_by(Favorite.saved_at.desc()).all()
        return [f.__dict__ for f in favs]
    finally:
        session.close()


def is_favorite(user_id, city, month):
    session = get_session()
    try:
        return session.query(Favorite).filter_by(
            user_id=user_id, city=city, month=month
        ).first() is not None
    finally:
        session.close()


# ─── SEARCH HISTORY ─────────────────────────────────────

def save_search(user_id, month, preferences, top_result):
    session = get_session()
    try:
        session.add(SearchHistory(
            user_id=user_id,
            month=month,
            preferences=json.dumps(preferences),
            top_result=top_result,
            searched_at=datetime.now().isoformat()
        ))
        session.commit()
    finally:
        session.close()


def get_search_history(user_id, limit=10):
    session = get_session()
    try:
        rows = session.query(SearchHistory)\
            .filter_by(user_id=user_id)\
            .order_by(SearchHistory.searched_at.desc())\
            .limit(limit)\
            .all()

        return [
            {
                "id": r.id,
                "month": r.month,
                "preferences": json.loads(r.preferences),
                "top_result": r.top_result,
                "searched_at": r.searched_at
            }
            for r in rows
        ]
    finally:
        session.close()


# ─── INTERESTS ──────────────────────────────────────────

def register_user(username, email, password, interests: dict):
    """Version avec intérêts (SQLAlchemy)"""
    session = get_session()
    try:
        salt = secrets.token_hex(16)
        hashed = _hash_password(password, salt)

        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            password=hashed,
            salt=salt,
            created_at=datetime.now().isoformat()
        )

        session.add(user)
        session.flush()  # pour récupérer user.id

        session.add(UserInterests(
            user_id=user.id,
            interests=json.dumps(interests),
            updated_at=datetime.now().isoformat()
        ))

        session.commit()
        return {"success": True, "user_id": user.id}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}

    finally:
        session.close()


def get_user_interests(user_id: int):
    session = get_session()
    try:
        row = session.query(UserInterests).filter_by(user_id=user_id).first()

        if row:
            return json.loads(row.interests)

        return {
            "nature": 3,
            "patrimoine": 3,
            "culture": 3,
            "restaurant": 3,
            "nightlife": 3,
            "loisirs": 3
        }
    finally:
        session.close()


def update_user_interests(user_id: int, interests: dict):
    session = get_session()
    try:
        row = session.query(UserInterests).filter_by(user_id=user_id).first()
        now = datetime.now().isoformat()

        if row:
            row.interests = json.dumps(interests)
            row.updated_at = now
        else:
            row = UserInterests(
                user_id=user_id,
                interests=json.dumps(interests),
                updated_at=now
            )
            session.add(row)

        session.commit()
        return {"success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}

    finally:
        session.close()