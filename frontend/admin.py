"""
admin.py — Page d'administration TravelMatch
Accessible uniquement aux utilisateurs avec is_admin = 1
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import sys
import os

sys.path.append(os.path.abspath(".."))

from backend.database import get_connection, get_search_history
from datetime import datetime, timedelta


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
#  REQUÊTES ANALYTICS
# ─────────────────────────────────────────────


def get_user_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    total_admins = c.fetchone()[0]

    # Inscriptions des 30 derniers jours
    since = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (since,))
    new_users_30d = c.fetchone()[0]

    # Inscriptions par jour (30 derniers jours)
    c.execute(
        """
        SELECT substr(created_at, 1, 10) as day, COUNT(*) as nb
        FROM users WHERE created_at >= ?
        GROUP BY day ORDER BY day
    """,
        (since,),
    )
    signups_by_day = [{"date": r[0], "inscriptions": r[1]} for r in c.fetchall()]

    conn.close()
    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "new_users_30d": new_users_30d,
        "signups_by_day": signups_by_day,
    }


def get_search_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM search_history")
    total_searches = c.fetchone()[0]

    # Destinations les plus recherchées
    c.execute(
        """
        SELECT top_result, COUNT(*) as nb
        FROM search_history
        WHERE top_result IS NOT NULL
        GROUP BY top_result
        ORDER BY nb DESC LIMIT 10
    """
    )
    top_destinations = [{"city": r[0], "recherches": r[1]} for r in c.fetchall()]

    # Mois les plus populaires
    c.execute(
        """
        SELECT month, COUNT(*) as nb
        FROM search_history
        GROUP BY month ORDER BY nb DESC
    """
    )
    months_raw = c.fetchall()

    month_names = {
        1: "Janvier",
        2: "Février",
        3: "Mars",
        4: "Avril",
        5: "Mai",
        6: "Juin",
        7: "Juillet",
        8: "Août",
        9: "Septembre",
        10: "Octobre",
        11: "Novembre",
        12: "Décembre",
    }
    top_months = [{"mois": month_names.get(r[0], str(r[0])), "recherches": r[1]} for r in months_raw]

    # Recherches par jour (30 derniers jours)
    since = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute(
        """
        SELECT substr(searched_at, 1, 10) as day, COUNT(*) as nb
        FROM search_history WHERE searched_at >= ?
        GROUP BY day ORDER BY day
    """,
        (since,),
    )
    searches_by_day = [{"date": r[0], "recherches": r[1]} for r in c.fetchall()]

    # Température moyenne souhaitée
    c.execute("SELECT preferences FROM search_history")
    temps = []
    for row in c.fetchall():
        try:
            prefs = json.loads(row[0])
            if "temp_avg" in prefs:
                temps.append(float(prefs["temp_avg"]))
        except Exception:
            pass
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None

    conn.close()
    return {
        "total_searches": total_searches,
        "top_destinations": top_destinations,
        "top_months": top_months,
        "searches_by_day": searches_by_day,
        "avg_temp_wanted": avg_temp,
    }


def get_favorites_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM favorites")
    total_favs = c.fetchone()[0]

    # Villes les plus mises en favoris
    c.execute(
        """
        SELECT city, country, COUNT(*) as nb
        FROM favorites
        GROUP BY city ORDER BY nb DESC LIMIT 10
    """
    )
    top_cities = [{"city": r[0], "country": r[1] or "", "favoris": r[2]} for r in c.fetchall()]

    # Mois les plus mis en favoris
    c.execute(
        """
        SELECT month, COUNT(*) as nb
        FROM favorites GROUP BY month ORDER BY nb DESC
    """
    )
    month_names = {
        1: "Janvier",
        2: "Février",
        3: "Mars",
        4: "Avril",
        5: "Mai",
        6: "Juin",
        7: "Juillet",
        8: "Août",
        9: "Septembre",
        10: "Octobre",
        11: "Novembre",
        12: "Décembre",
    }
    top_months = [{"mois": month_names.get(r[0], str(r[0])), "favoris": r[1]} for r in c.fetchall()]

    conn.close()
    return {
        "total_favs": total_favs,
        "top_cities": top_cities,
        "top_months": top_months,
    }


def get_all_users() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT u.id, u.username, u.email, u.created_at, u.is_admin,
               COUNT(DISTINCT s.id) as nb_searches,
               COUNT(DISTINCT f.id) as nb_favs
        FROM users u
        LEFT JOIN search_history s ON s.user_id = u.id
        LEFT JOIN favorites f ON f.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def delete_user(user_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM favorites      WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM user_interests  WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM profiles        WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users           WHERE id = ?", (user_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def toggle_admin(user_id: int, current_value: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 - current_value, user_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  PAGE ADMIN
# ─────────────────────────────────────────────


def show_admin_page(user: dict):
    if not require_admin(user):
        return

    st.markdown(
        """
    <div style="font-family:'Playfair Display',serif; font-size:2.2rem;
                color:#0f172a; margin-bottom:0.2rem;">
        🛠️ Administration
    </div>
    <div style="color:#64748b; font-size:0.95rem; margin-bottom:1.5rem;">
        Monitoring et gestion de TravelMatch
    </div>
    """,
        unsafe_allow_html=True,
    )

    tab_overview, tab_searches, tab_favs, tab_users = st.tabs(
        [
            "📊 Vue d'ensemble",
            "🔍 Recherches",
            "❤️ Favoris",
            "👥 Utilisateurs",
        ]
    )

    # ── VUE D'ENSEMBLE ───────────────────────────────────────────
    with tab_overview:
        u_stats = get_user_stats()
        s_stats = get_search_stats()
        f_stats = get_favorites_stats()

        # KPIs
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("👤 Utilisateurs", u_stats["total_users"])
        k2.metric("🆕 Nouveaux (30j)", u_stats["new_users_30d"])
        k3.metric("🔍 Recherches total", s_stats["total_searches"])
        k4.metric("❤️ Favoris total", f_stats["total_favs"])
        k5.metric(
            "🌡️ Temp. souhaitée",
            f"{s_stats['avg_temp_wanted']}°C" if s_stats["avg_temp_wanted"] else "N/A",
        )

        st.markdown("---")
        col1, col2 = st.columns(2)

        # Inscriptions par jour
        with col1:
            st.markdown("#### 📈 Inscriptions (30 derniers jours)")
            if u_stats["signups_by_day"]:
                df_signup = pd.DataFrame(u_stats["signups_by_day"])
                fig = px.area(
                    df_signup,
                    x="date",
                    y="inscriptions",
                    color_discrete_sequence=["#0ea5e9"],
                )
                fig.update_layout(
                    margin=dict(t=10, b=30, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=220,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée.")

        # Recherches par jour
        with col2:
            st.markdown("#### 🔍 Recherches (30 derniers jours)")
            if s_stats["searches_by_day"]:
                df_search = pd.DataFrame(s_stats["searches_by_day"])
                fig = px.area(
                    df_search,
                    x="date",
                    y="recherches",
                    color_discrete_sequence=["#6366f1"],
                )
                fig.update_layout(
                    margin=dict(t=10, b=30, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=220,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée.")

    # ── RECHERCHES ───────────────────────────────────────────────
    with tab_searches:
        s_stats = get_search_stats()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏆 Top 10 destinations recherchées")
            if s_stats["top_destinations"]:
                df_dest = pd.DataFrame(s_stats["top_destinations"])
                fig = px.bar(
                    df_dest,
                    x="recherches",
                    y="city",
                    orientation="h",
                    color="recherches",
                    color_continuous_scale=["#bae6fd", "#0ea5e9", "#0369a1"],
                )
                fig.update_layout(
                    showlegend=False,
                    coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune recherche enregistrée.")

        with col2:
            st.markdown("#### 🗓️ Mois les plus populaires")
            if s_stats["top_months"]:
                df_months = pd.DataFrame(s_stats["top_months"])
                fig = px.bar(
                    df_months,
                    x="mois",
                    y="recherches",
                    color="recherches",
                    color_continuous_scale=["#ddd6fe", "#6366f1", "#4338ca"],
                )
                fig.update_layout(
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(t=10, b=40, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée.")

    # ── FAVORIS ──────────────────────────────────────────────────
    with tab_favs:
        f_stats = get_favorites_stats()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏙️ Villes les plus mises en favoris")
            if f_stats["top_cities"]:
                df_cities = pd.DataFrame(f_stats["top_cities"])
                df_cities["label"] = df_cities["city"] + " (" + df_cities["country"] + ")"
                fig = px.bar(
                    df_cities,
                    x="favoris",
                    y="label",
                    orientation="h",
                    color="favoris",
                    color_continuous_scale=["#fce7f3", "#ec4899", "#be185d"],
                )
                fig.update_layout(
                    showlegend=False,
                    coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucun favori enregistré.")

        with col2:
            st.markdown("#### 🗓️ Mois des destinations favorites")
            if f_stats["top_months"]:
                df_fav_months = pd.DataFrame(f_stats["top_months"])
                fig = px.pie(
                    df_fav_months,
                    names="mois",
                    values="favoris",
                    color_discrete_sequence=px.colors.sequential.RdPu,
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    font=dict(family="Outfit"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée.")

    # ── UTILISATEURS ─────────────────────────────────────────────
    with tab_users:
        st.markdown("#### 👥 Gestion des utilisateurs")

        users = get_all_users()
        if not users:
            st.info("Aucun utilisateur.")
            return

        # Recherche
        search_query = st.text_input("🔎 Rechercher un utilisateur", placeholder="Nom ou email...")
        if search_query:
            users = [
                u
                for u in users
                if search_query.lower() in u["username"].lower() or search_query.lower() in u["email"].lower()
            ]

        st.markdown(f"**{len(users)} utilisateur(s)**")

        for u in users:
            is_current = u["id"] == user["id"]
            created = u["created_at"][:10]
            role_badge = "🔴 Admin" if u["is_admin"] else "👤 User"

            with st.expander(
                f"{role_badge}  **{u['username']}** — {u['email']}  ·  inscrit le {created}",
                expanded=False,
            ):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    st.markdown(f"**Email :** {u['email']}")
                    st.caption(f"ID : {u['id']} · Inscrit le {created}")
                with c2:
                    st.metric("🔍 Recherches", u["nb_searches"])
                with c3:
                    st.metric("❤️ Favoris", u["nb_favs"])
                with c4:
                    if not is_current:
                        # Toggle admin
                        admin_label = "⬇️ Retirer admin" if u["is_admin"] else "⬆️ Rendre admin"
                        if st.button(
                            admin_label,
                            key=f"admin_{u['id']}",
                            use_container_width=True,
                        ):
                            toggle_admin(u["id"], u["is_admin"])
                            st.toast(f"Rôle mis à jour pour {u['username']}")
                            st.rerun()

                        # Suppression
                        if st.button(
                            "🗑️ Supprimer",
                            key=f"del_{u['id']}",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state[f"confirm_del_{u['id']}"] = True

                        # Confirmation suppression
                        if st.session_state.get(f"confirm_del_{u['id']}"):
                            st.warning(f"⚠️ Supprimer **{u['username']}** et toutes ses données ?")
                            cc1, cc2 = st.columns(2)
                            with cc1:
                                if st.button(
                                    "✅ Confirmer",
                                    key=f"confirm_yes_{u['id']}",
                                    type="primary",
                                ):
                                    delete_user(u["id"])
                                    st.session_state.pop(f"confirm_del_{u['id']}", None)
                                    st.toast(f"Utilisateur {u['username']} supprimé.")
                                    st.rerun()
                            with cc2:
                                if st.button("❌ Annuler", key=f"confirm_no_{u['id']}"):
                                    st.session_state.pop(f"confirm_del_{u['id']}", None)
                                    st.rerun()
                    else:
                        st.caption("_(compte actuel)_")
