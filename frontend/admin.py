"""
admin.py — Page d'administration TravelMatch
Accessible uniquement aux utilisateurs avec is_admin = 1
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests

# Récupération de l'URL du Backend FastAPI depuis le docker-compose
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────
#  VÉRIFICATION ADMIN
# ─────────────────────────────────────────────

def is_admin(user: dict) -> bool:
    return bool(user.get("is_admin", 0))

def require_admin(user: dict) -> bool:
    """Retourne True si admin, affiche une erreur sinon."""
    if not is_admin(user):
        st.error("🚫 Accès refusé — réservé aux administrateurs.")
        return False
    return True

# ─────────────────────────────────────────────
#  REQUÊTES API (Remplacent le SQL direct)
# ─────────────────────────────────────────────

def get_user_stats() -> dict:
    """Récupère les statistiques globales via l'API."""
    try:
        response = requests.get(f"{API_URL}/api/admin/stats")
        if response.status_code == 200:
            return response.json()
        st.error(f"Erreur lors du chargement des stats ({response.status_code})")
        return {"total_users": 0, "total_admins": 0}
    except Exception as e:
        st.error(f"Erreur de connexion au backend : {e}")
        return {"total_users": 0, "total_admins": 0}

def get_all_users() -> list:
    """Récupère la liste de tous les utilisateurs via l'API."""
    try:
        response = requests.get(f"{API_URL}/api/admin/users")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Impossible de récupérer les utilisateurs : {e}")
        return []

def delete_user(user_id: int) -> bool:
    """Demande la suppression d'un utilisateur au backend."""
    try:
        response = requests.delete(f"{API_URL}/api/admin/users/{user_id}")
        if response.status_code == 200:
            return True
        st.error(f"Erreur de suppression ({response.status_code})")
        return False
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return False

def get_admin_search_history() -> list:
    """Récupère l'historique global de recherche via l'API."""
    try:
        response = requests.get(f"{API_URL}/api/admin/history")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Impossible de récupérer l'historique : {e}")
        return []

# ─────────────────────────────────────────────
#  INTERFACE GRAPHIQUE (UI)
# ─────────────────────────────────────────────

def show_admin_page():
    """Affiche le tableau de bord d'administration."""
    current_user = st.session_state.get("user")
    if not current_user or not require_admin(current_user):
        return

    st.title("🛠️ Panneau d'Administration")
    st.markdown("Bienvenue dans l'espace de gestion et d'analyse de TravelMatch.")

    # 1. KPIs / Statistiques
    stats = get_user_stats()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Utilisateurs Inscrits", stats.get("total_users", 0))
    with c2:
        st.metric("Administrateurs", stats.get("total_admins", 0))

    st.markdown("---")

    # Onglets de gestion
    tab_users, tab_history = st.tabs(["👥 Gestion Utilisateurs", "📊 Historique & Analytics"])

    with tab_users:
        st.subheader("Liste des comptes")
        users = get_all_users()

        if not users:
            st.info("Aucun utilisateur trouvé.")
        else:
            for u in users:
                col_info, col_action = st.columns([4, 1])
                with col_info:
                    badge = "🛡️ Admin" if u["is_admin"] else "👤 User"
                    st.markdown(f"**{u['username']}** ({u['email']}) — `{badge}`")
                
                with col_action:
                    # Empêcher l'admin de se supprimer lui-même
                    if u["id"] != current_user.get("id"):
                        if st.button("🗑️ Supprimer", key=f"del_{u['id']}", type="secondary"):
                            st.session_state[f"confirm_del_{u['id']}"] = True

                        if st.session_state.get(f"confirm_del_{u['id']}"):
                            st.warning(f"Confirmer la suppression de {u['username']} ?")
                            cc1, cc2 = st.columns(2)
                            with cc1:
                                if st.button("✅ Oui", key=f"yes_{u['id']}", type="primary"):
                                    if delete_user(u["id"]):
                                        st.session_state.pop(f"confirm_del_{u['id']}", None)
                                        st.toast("Utilisateur supprimé !")
                                        st.rerun()
                            with cc2:
                                if st.button("❌ Non", key=f"no_{u['id']}"):
                                    st.session_state.pop(f"confirm_del_{u['id']}", None)
                                    st.rerun()
                    else:
                        st.caption("_(votre compte)_")

    with tab_history:
        st.subheader("Historique des requêtes")
        history_data = get_admin_search_history()

        if not history_data:
            st.info("Aucune recherche enregistrée pour le moment.")
        else:
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)

            # Graphique Analytics
            if not df.empty and "query" in df.columns:
                st.markdown("### 🔝 Top Destinations Recherchées")
                top_queries = df["query"].value_counts().reset_index()
                top_queries.columns = ["Destination", "Nombre"]
                fig = px.bar(top_queries.head(10), x="Destination", y="Nombre", color="Nombre")
                st.plotly_chart(fig, use_container_width=True)