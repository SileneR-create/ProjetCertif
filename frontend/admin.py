"""
admin.py — Page d'administration TravelMatch (Version Graphiques Clairs + Top Favoris)
Accessible uniquement aux utilisateurs avec is_admin = 1
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import datetime, timedelta

# Récupération de l'URL du Backend FastAPI depuis le docker-compose
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────
#  VÉRIFICATION ADMIN
# ─────────────────────────────────────────────

def is_admin(user: dict) -> bool:
    return bool(user.get("is_admin", 0))

def require_admin(user: dict) -> bool:
    if not is_admin(user):
        st.error("🚫 Accès refusé — réservé aux administrateurs.")
        return False
    return True

# ─────────────────────────────────────────────
#  REQUÊTES API
# ─────────────────────────────────────────────

def get_user_stats() -> dict:
    try:
        response = requests.get(f"{API_URL}/api/admin/stats")
        if response.status_code == 200:
            return response.json()
        return {"total_users": 0, "total_admins": 0}
    except Exception:
        return {"total_users": 0, "total_admins": 0}

def get_all_users() -> list:
    try:
        response = requests.get(f"{API_URL}/api/admin/users")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

def delete_user(user_id: int) -> bool:
    try:
        response = requests.delete(f"{API_URL}/api/admin/users/{user_id}")
        return response.status_code == 200
    except Exception:
        return False

def get_admin_search_history() -> list:
    try:
        response = requests.get(f"{API_URL}/api/admin/history")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

def get_top_favorites() -> list:
    """Nouvelle requête pour récupérer le classement des favoris globaux."""
    try:
        response = requests.get(f"{API_URL}/api/admin/favorites/top")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

# ─────────────────────────────────────────────
#  INTERFACE GRAPHIQUE (UI)
# ─────────────────────────────────────────────

def show_admin_page():
    current_user = st.session_state.get("user")
    if not current_user or not require_admin(current_user):
        return

    st.title("🛠️ Panneau d'Administration & Analytics")
    st.markdown("Suivi des performances, des tendances et des coups de cœur des utilisateurs.")

    # Chargement des données historiques
    history_data = get_admin_search_history()
    df_history = pd.DataFrame(history_data)
    
    fav_data = get_top_favorites()
    df_fav = pd.DataFrame(fav_data)
    
    # ─── SECTION 1 : VRAIS KPIS BUSINESS ───────────────────
    stats = get_user_stats()
    
    total_searches = len(df_history) if not df_history.empty else 0
    searches_24h = 0
    total_saved_favs = df_fav["count"].sum() if not df_fav.empty else 0
    
    if total_searches > 0 and "searched_at" in df_history.columns:
        try:
            df_history["datetime"] = pd.to_datetime(df_history["searched_at"])
            one_day_ago = datetime.now() - timedelta(days=1)
            searches_24h = df_history[df_history["datetime"] > one_day_ago].shape[0]
        except Exception:
            pass

    # Affichage des compteurs
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.metric(label="👥 Utilisateurs Inscrits", value=stats.get("total_users", 0))
    with kpi_col2:
        st.metric(label="📊 Recherches Totales", value=total_searches)
    with kpi_col3:
        st.metric(label="⚡ Activité (24h)", value=searches_24h)
    with kpi_col4:
        st.metric(label="❤️ total Favoris Enregistrés", value=int(total_saved_favs))

    st.markdown("---")

    # Onglets de gestion
    tab_analytics, tab_users = st.tabs(["📊 Analytics Visuels", "👥 Gestion des Comptes"])

    with tab_analytics:
        # --- BLOC 1 : LES INTENTIONS (RECHERCHES VS FAVORIS) ---
        st.subheader("💡 Analyse des Tendances de Voyage")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 🗺️ Top des résultats d'affichage (Visibilité)")
            
            if df_history.empty:
                st.info("Aucune donnée d'affichage enregistrée.")
            else:
                # 1. On s'assure d'extraire la colonne contenant le nom de la ville
                # Si ton API renvoie la colonne sous le nom 'city'
                if "city" in df_history.columns:
                    df_counts = df_history["city"].value_counts().reset_index()
                    df_counts.columns = ["Ville", "Nombre d'affichages"]
                else:
                    # Sécurité si l'API utilise encore l'ancienne colonne 'query'
                    df_counts = df_history["query"].value_counts().reset_index()
                    df_counts.columns = ["Ville", "Nombre d'affichages"]
                
                # En force le type en texte pour éviter les bugs d'affichage de Plotly
                df_counts["Ville"] = df_counts["Ville"].astype(str)
                
                # 2. On garde le Top 8 pour la clarté visuelle
                df_top_visible = df_counts.head(8)
                
                # 3. Construction du Bar Chart Vertical épuré
                fig_top_results = px.bar(
                    df_top_visible,
                    x="Ville",
                    y="Nombre d'affichages",
                    color="Ville",
                    text="Nombre d'affichages",  # Affiche le score en gros au-dessus de la barre
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                
                # 4. Nettoyage du design pour une interprétation immédiate
                fig_top_results.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>Affichages : %{y}"
                )
                
                fig_top_results.update_layout(
                    showlegend=False,  # Supprime la légende inutile à droite
                    xaxis_title=None,  # Supprime le titre d'axe "Ville" sous les noms
                    yaxis_title="Nombre de fois proposée",
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=380
                )
                
                st.plotly_chart(fig_top_results, use_container_width=True)

        with col_right:
            st.markdown("#### ❤️ Top des Villes ajoutées en Favoris (Coups de cœur)")
            if df_fav.empty:
                st.info("Aucun favori enregistré pour le moment.")
            else:
                df_fav.columns = ["Ville", "Nombre d'ajouts"]
                # Graphique à barres horizontales pour une lecture ultra rapide des noms longs
                fig_bar = px.bar(
                    df_fav.head(8),
                    x="Nombre d'ajouts",
                    y="Ville",
                    orientation='h',
                    color="Nombre d'ajouts",
                    color_continuous_scale="Viridis"
                )
                # Trier pour avoir le plus grand en haut
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        
        # --- BLOC 2 : VOLUMÉTRIE TEMPORELLE ---
        if not df_history.empty and "datetime" in df_history.columns:
            st.markdown("### 📈 Évolution du volume de requêtes")
            df_history["date"] = df_history["datetime"].dt.date
            df_timeline = df_history.groupby("date").size().reset_index(name="Nombre de requêtes")
            
            fig_line = px.line(
                df_timeline, 
                x="date", 
                y="Nombre de requêtes",
                markers=True,
                line_shape="spline"
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # --- BLOC 3 : LE TABLEAU DE BORD BRUT ---
        st.markdown("### 📋 Journal de l'activité globale")
        if not df_history.empty:
            st.dataframe(df_history[["username", "month", "query", "searched_at"]], use_container_width=True)
        else:
            st.info("Aucune activité.")

    with tab_users:
        # (Le code de gestion des utilisateurs reste identique à l'étape précédente...)
        st.subheader("Liste des comptes enregistrés")
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