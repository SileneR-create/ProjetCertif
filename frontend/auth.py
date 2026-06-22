"""
auth.py — Composants UI pour l'authentification dans Streamlit
Modifié pour communiquer exclusivement via l'API FastAPI (Architecture Découplée)
"""

import streamlit as st
import sys
import os
import requests  

# Configuration de l'URL de l'API (gérée par Docker ou localhost par défaut)
API_URL = os.getenv("API_URL", "http://localhost:8000")


# ─────────────────────────────────────────────
#  GESTION SESSION
# ─────────────────────────────────────────────


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("token", None)
    st.session_state.pop("auth_tab", None)
    st.rerun()


def auth_headers() -> dict:
    """Retourne l'en-tête Authorization Bearer pour les appels API protégés."""
    token = st.session_state.get("token", "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────
#  CSS AUTH
# ─────────────────────────────────────────────

AUTH_CSS = """
<style>
.auth-container {
    max-width: 420px;
    margin: 3rem auto;
    padding: 2.5rem;
    background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%);
    border-radius: 20px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 25px rgba(148, 163, 184, 0.1);
}
.auth-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1e3a8a;
    text-align: center;
    margin-bottom: 0.5rem;
}
.auth-subtitle {
    font-size: 0.95rem;
    color: #64748b;
    text-align: center;
    margin-bottom: 2rem;
}
</style>
"""

# ─────────────────────────────────────────────
#  INTERFACE UI & LOGIQUE DE CONNEXION
# ─────────────────────────────────────────────


def show_auth_page():
    """Affiche le formulaire stylisé d'authentification (Login / Register)"""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-title">TravelMatch ✈️</div>
            <div class="auth-subtitle">Trouvez la destination parfaite pour vos vacances</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Onglets de sélection de mode
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Création de compte"])

    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Nom d'utilisateur", key="login_user")
        password = st.text_input("Mot de passe", type="password", key="login_pass")

        if st.button("Se connecter", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                try:
                    # 🌐 Appel de la route de connexion sur FastAPI
                    response = requests.post(f"{API_URL}/auth/login", json={"username": username, "password": password})

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state["user"] = result["user"]
                        st.session_state["token"] = result.get("access_token", "")
                        st.success("Connexion réussie ! Connexion en cours... 🎉")
                        st.rerun()
                    else:
                        # Si le backend renvoie une erreur (401, 400...), on extrait le détail
                        error_detail = response.json().get("detail", "Identifiants incorrects.")
                        st.error(error_detail)

                except Exception as e:
                    st.error(f"Erreur de connexion au serveur backend : {e}")

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        new_username = st.text_input("Nom d'utilisateur", key="reg_user")
        new_email = st.text_input("Adresse Email", key="reg_email")
        new_password = st.text_input("Mot de passe", type="password", key="reg_pass")

        st.markdown("#### 🎯 Vos préférences initiales")
        st.caption("Évaluez votre intérêt pour ces catégories (de 1 à 5)")

        c1, c2, c3 = st.columns(3)
        with c1:
            i_nature = st.slider("🍀 Nature / Grands Espaces", 1, 5, 3)
            i_resto = st.slider("🍳 Gastronomie", 1, 5, 3)
        with c2:
            i_patrimoine = st.slider("🏛️ Histoire & Monuments", 1, 5, 3)
            i_night = st.slider("🎉 Vie Nocturne", 1, 5, 3)
        with c3:
            i_culture = st.slider("🎨 Musées & Art", 1, 5, 3)
            i_loisirs = st.slider("🎢 Activités & Loisirs", 1, 5, 3)

        interests = {
            "nature": i_nature,
            "patrimoine": i_patrimoine,
            "culture": i_culture,
            "restaurant": i_resto,
            "nightlife": i_night,
            "loisirs": i_loisirs,
        }

        if st.button("Créer mon compte", type="primary", use_container_width=True):
            if not new_username or not new_email or not new_password:
                st.error("Veuillez remplir tous les champs obligatoires.")
            elif "@" not in new_email:
                st.error("Veuillez entrer une adresse email valide.")
            else:
                try:
                    # 🌐 Appel de la route d'inscription sur FastAPI
                    response = requests.post(
                        f"{API_URL}/auth/register",
                        json={
                            "username": new_username,
                            "email": new_email,
                            "password": new_password,
                            "interests": interests,
                        },
                    )

                    if response.status_code == 200:
                        st.success("Compte créé avec succès ! Authentification en cours...")

                        # Auto-login après inscription réussie
                        login_response = requests.post(
                            f"{API_URL}/auth/login", json={"username": new_username, "password": new_password}
                        )
                        if login_response.status_code == 200:
                            login_data = login_response.json()
                            st.session_state["user"] = login_data["user"]
                            st.session_state["token"] = login_data.get("access_token", "")
                            st.rerun()
                        else:
                            st.warning(
                                "Compte créé, mais la connexion automatique a échoué. Veuillez vous connecter manuellement."
                            )
                    else:
                        error_detail = response.json().get("detail", "Erreur lors de la création du compte.")
                        st.error(error_detail)

                except Exception as e:
                    st.error(f"Erreur de connexion au serveur backend : {e}")


# ─────────────────────────────────────────────
#  WIDGET UTILISATEUR (sidebar)
# ─────────────────────────────────────────────


def show_user_widget():
    """Affiche le widget utilisateur connecté dans la sidebar."""
    user = get_current_user()

    if not user:
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
    <div style="background: linear-gradient(135deg, #eef2ff, #f8faff);
                border-radius: 12px; padding: 0.8rem 1rem;
                border: 1px solid #e2e8f0;">
        <div style="font-weight: 600; color: #1a1a2e; font-size:0.95rem;">
            👤 {user['username']}
        </div>
        <div style="color: #64748b; font-size: 0.78rem; margin-top:2px;">
            {user['email']}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True, type="secondary"):
        logout()
