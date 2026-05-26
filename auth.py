"""
auth.py — Composants UI pour l'authentification dans Streamlit
"""

import streamlit as st
from backend.database import init_db, register_user, login_user

# Initialiser la DB au premier import
init_db()


# ─────────────────────────────────────────────
#  GESTION SESSION
# ─────────────────────────────────────────────


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("auth_tab", None)
    st.rerun()


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
    box-shadow: 0 8px 32px rgba(99,102,241,0.10);
}
.auth-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: #1a1a2e;
    text-align: center;
    margin-bottom: 0.3rem;
}
.auth-sub {
    text-align: center;
    color: #64748b;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}
.auth-divider {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.2rem 0;
}
</style>
"""


# ─────────────────────────────────────────────
#  PAGE LOGIN / REGISTER
# ─────────────────────────────────────────────


def show_auth_page():
    """Affiche la page de connexion/inscription."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    st.markdown(
        """
    <div style="text-align:center; margin-bottom: 2rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:2.8rem; color:#1a1a2e;">
            ✈️ TravelMatch
        </div>
        <div style="color:#64748b; font-size:1rem;">
            Connectez-vous pour sauvegarder vos destinations favorites
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["🔑 Connexion", "📝 Inscription"])

    # ── CONNEXION ──
    with tab_login:
        with st.form("login_form"):
            st.markdown("#### Bon retour ! 👋")
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button(
                "Se connecter", use_container_width=True, type="primary"
            )

            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    result = login_user(username, password)
                    if result["success"]:
                        st.session_state["user"] = result["user"]
                        st.success(f"Bienvenue {username} ! 🎉")
                        st.rerun()
                    else:
                        st.error(result["error"])

    # ── INSCRIPTION ──
    with tab_register:
        with st.form("register_form"):
            st.markdown("#### Créer un compte 🚀")
            new_username = st.text_input("Nom d'utilisateur")
            new_email = st.text_input("Email")
            new_password = st.text_input("Mot de passe", type="password")
            new_password2 = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button(
                "Créer mon compte", use_container_width=True, type="primary"
            )

            if submitted:
                if not all([new_username, new_email, new_password, new_password2]):
                    st.error("Veuillez remplir tous les champs.")
                elif new_password != new_password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    result = register_user(new_username, new_email, new_password)
                    if result["success"]:
                        # Connecter directement après inscription
                        login_result = login_user(new_username, new_password)
                        st.session_state["user"] = login_result["user"]
                        st.success("Compte créé avec succès ! Bienvenue 🎉")
                        st.rerun()
                    else:
                        st.error(result["error"])


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

    if user.get("is_admin"):
        if st.sidebar.button("🛠️ Administration", use_container_width=True):
            st.session_state["page"] = "admin"
            st.rerun()

    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        logout()
