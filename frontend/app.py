import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
import sys
import os


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from recommender import recommend, engineer_features, MONTH_NAMES, ACTIVITY_FEATURES
from auth import show_user_widget, is_logged_in, get_current_user
from backend.database import (init_db, add_favorite, remove_favorite, get_favorites,
    is_favorite, save_search, get_search_history, update_user_interests, get_user_interests, register_user, login_user
)
from admin import show_admin_page, is_admin
from backend.utils import get_cached_images, display_image_carousel

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TravelMatch",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BUDGET_MAP = {
    "🎒 Petit budget":   25,
    "✈️ Moyen":          55,
    "🏨 Confortable":    80,
    "💎 Luxe":           100,
}

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Outfit:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 3rem; color: #0f172a; line-height: 1.15;
    margin-bottom: 0.4rem;
}
.hero-sub { font-size: 1.05rem; color: #64748b; font-weight: 300; margin-bottom: 1.5rem; }

.sidebar-section {
    font-family: 'Playfair Display', serif;
    font-size: 0.95rem; color: #0f172a;
    border-bottom: 2px solid #0ea5e9;
    padding-bottom: 0.3rem; margin: 1.2rem 0 0.8rem 0;
}

.dest-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 1px solid #bae6fd; border-radius: 16px;
    padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
    border-left: 4px solid #0ea5e9;
}
.dest-rank  { font-size: 0.75rem; color: #0ea5e9; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.dest-name  { font-family: 'Playfair Display', serif; font-size: 1.5rem; color: #0f172a; }
.dest-score { font-size: 2rem; font-weight: 700; color: #0ea5e9; }
.dest-cluster { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }

.star-row { font-size: 1.4rem; letter-spacing: 0.1em; }

.profile-card {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border-radius: 12px; padding: 1rem 1.2rem;
    border: 1px solid #bae6fd; margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  DONNÉES
# ─────────────────────────────────────────────
DATA_PATH = r"..\DATA\processed\data_clean.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = engineer_features(df)

    col = "Revenu moyen par habitant ($/jour)"
    q1 = df[col].quantile(0.25)
    q2 = df[col].quantile(0.50)
    q3 = df[col].quantile(0.75)

    st.session_state["budget_quartiles"] = {
        "🎒 Petit budget":  (0,  q1),
        "✈️ Moyen":         (q1, q2),
        "🏨 Confortable":   (q2, q3),
        "💎 Luxe":          (q3, float("inf")),
        "quartiles": (round(q1,1), round(q2,1), round(q3,1))
    }
    return df


# ─────────────────────────────────────────────
#  COMPOSANT ÉTOILES
# ─────────────────────────────────────────────
def star_rating(label: str, key: str, default: int = 3) -> int:
    """Affiche un sélecteur d'étoiles via un slider discret stylisé."""
    val = st.slider(label, 1, 5, value=default, key=key,
                    format="%d ⭐")
    stars = "★" * val + "☆" * (5 - val)
    st.markdown(f'<div class="star-row" style="color:#f59e0b">{stars}</div>', unsafe_allow_html=True)
    return val


# ─────────────────────────────────────────────
#  PAGE INSCRIPTION
# ─────────────────────────────────────────────
def show_auth_page():

    st.markdown("""
    <div style="text-align:center; padding: 2rem 0 1rem;">
        <div style="font-family:'Playfair Display',serif; font-size:3rem; color:#0f172a;">✈️ TravelMatch</div>
        <div style="color:#64748b; font-size:1rem; font-weight:300;">
            Votre destination idéale, calculée sur mesure.
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Connexion", "📝 Créer un compte"])

    # ── CONNEXION ──
    with tab_login:
        with st.form("login_form"):
            st.markdown("#### Bon retour 👋")
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Remplissez tous les champs.")
                else:
                    result = login_user(username, password)
                    if result["success"]:
                        st.session_state["user"] = result["user"]
                        st.rerun()
                    else:
                        st.error(result["error"])

    # ── INSCRIPTION ──
    with tab_register:
        with st.form("register_form"):
            st.markdown("#### Créer mon compte")
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Nom d'utilisateur")
                new_password = st.text_input("Mot de passe", type="password")
            with c2:
                new_email    = st.text_input("Email")
                new_password2 = st.text_input("Confirmer le mot de passe", type="password")

            st.markdown("---")
            st.markdown("#### 🎯 Vos centres d'intérêt")
            st.caption("Ces préférences guident nos recommandations. Vous pourrez les modifier dans votre profil.")

            cols = st.columns(3)
            interests = {}
            fields = [
                ("nature",     "🌿 Nature"),
                ("patrimoine", "🏛️ Patrimoine"),
                ("culture",    "🎭 Culture"),
                ("restaurant", "🍽️ Gastronomie"),
                ("nightlife",  "🎉 Nightlife"),
                ("loisirs",    "🎢 Loisirs"),
            ]
            for i, (key, label) in enumerate(fields):
                with cols[i % 3]:
                    interests[key] = st.slider(label, 1, 5, 3,
                                               format="%d ⭐",
                                               key=f"reg_{key}")
                    stars = "★" * interests[key] + "☆" * (5 - interests[key])
                    st.markdown(f'<div style="color:#f59e0b;font-size:1.1rem">{stars}</div>',
                                unsafe_allow_html=True)

            if st.form_submit_button("Créer mon compte ✈️", use_container_width=True, type="primary"):
                if not all([new_username, new_email, new_password, new_password2]):
                    st.error("Remplissez tous les champs.")
                elif new_password != new_password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_password) < 6:
                    st.error("Mot de passe trop court (min. 6 caractères).")
                else:
                    result = register_user(new_username, new_email, new_password, interests)
                    if result["success"]:
                        login_result = login_user(new_username, new_password)
                        st.session_state["user"] = login_result["user"]
                        st.success("Compte créé ! Bienvenue 🎉")
                        st.rerun()
                    else:
                        st.error(result["error"])


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
def build_sidebar():
    st.sidebar.markdown("## ✈️ TravelMatch")
    st.sidebar.markdown("*Affinez votre recherche*")
    st.sidebar.markdown("---")

    # ── MOIS ────────────────────────────────────────────────────
    st.sidebar.markdown('<div class="sidebar-section">🗓️ Période</div>', unsafe_allow_html=True)
    month_name = st.sidebar.selectbox(
        "Mois du séjour",
        list(MONTH_NAMES.values()),
        index=st.session_state.get("month_index", 6),
        key="month_select"
    )
    month = [k for k, v in MONTH_NAMES.items() if v == month_name][0]

    # ── TEMPÉRATURE ─────────────────────────────────────────────
    st.sidebar.markdown('<div class="sidebar-section">🌡️ Climat</div>', unsafe_allow_html=True)
    temp_avg = st.sidebar.slider(
        "Température souhaitée (°C)", -10, 40,
        key="temp_slider"
    )
    st.sidebar.caption(f"Je veux environ {temp_avg}°C")

    # ── TYPE DE DESTINATION ──────────────────────────────────────
    st.sidebar.markdown('<div class="sidebar-section">🗺️ Type de destination</div>', unsafe_allow_html=True)
    cluster_options = {
        "Pas de préférence":        None,
        "🌿 Nature & Aventure":     0,
        "🏛️ Patrimoine & Histoire": 1,
        "🎭 Culture & Arts":        2,
        "🌊 Détente & Plages":      3,
        "🏙️ Métropole Moderne":     4,
        "🎉 Fête & Nightlife":      5,
    }
    cluster_choice  = st.sidebar.selectbox("Je cherche...", list(cluster_options.keys()), key="cluster_select")
    cluster_bonus   = cluster_options[cluster_choice]

    # ── CONFORT & SÉCURITÉ ───────────────────────────────────────
    st.sidebar.markdown('<div class="sidebar-section">🛡️ Confort & Sécurité</div>', unsafe_allow_html=True)
    indice_confort  = st.sidebar.slider("Confort sanitaire",  0, 100, 70, key="slider_confort")
    indice_securite = st.sidebar.slider("Niveau de sécurité", 0, 100, 60, key="slider_securite")

    # ── BUDGET ───────────────────────────────────────────────────
    st.sidebar.markdown('<div class="sidebar-section">💰 Budget</div>', unsafe_allow_html=True)
    budget_label = st.sidebar.radio(
        "Niveau de vie du pays",
        list(BUDGET_MAP.keys()),
        index=1,
        key="budget_radio",
        help="Correspond au niveau de développement économique de la destination"
    )
    budget_val = BUDGET_MAP[budget_label]

    # ── NOMBRE DE RÉSULTATS ─────────────────────────────────────
    st.sidebar.markdown("---")
    top_n = st.sidebar.number_input("Nombre de destinations", min_value=3, max_value=20, value=10)

    prefs = {
        "temp_avg":        temp_avg,
        "indice_confort":  indice_confort,
        "indice_securite": indice_securite,
        "budget_pct":      budget_val,
    }

    user = get_current_user()



    return month, prefs, top_n, cluster_bonus


# ─────────────────────────────────────────────
#  RADAR CHART
# ─────────────────────────────────────────────
def radar_chart(city_row: pd.Series, user_interests: dict, city_name: str):
    categories = ["Nature", "Patrimoine", "Culture", "Restaurant", "Nightlife", "Loisirs"]
    keys       = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]

    city_vals = [float(city_row.get(k, 0)) for k in keys]
    user_vals = [float(user_interests.get(k, 0)) for k in keys]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=city_vals + [city_vals[0]], theta=categories + [categories[0]],
        fill='toself', name=city_name,
        fillcolor='rgba(14,165,233,0.25)',
        line=dict(color='#0ea5e9', width=3),
    ))
    fig.add_trace(go.Scatterpolar(
        r=user_vals + [user_vals[0]], theta=categories + [categories[0]],
        fill='toself', name='Vos envies',
        fillcolor='rgba(245,158,11,0.0)',
        line=dict(color='#f59e0b', width=2, dash='dash'),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5],
                                   tickvals=[1,2,3,4,5], tickfont=dict(size=9))),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        height=300,
        margin=dict(t=20, b=40, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Outfit'),
    )
    return fig


# ─────────────────────────────────────────────
#  CARTE
# ─────────────────────────────────────────────
def build_map(results: pd.DataFrame):
    if "latitude" not in results.columns or "longitude" not in results.columns:
        return None
    m = folium.Map(
        location=[results["latitude"].mean(), results["longitude"].mean()],
        zoom_start=2, tiles="CartoDB positron"
    )
    colors = ["#0ea5e9","#6366f1","#ec4899","#f59e0b","#10b981",
              "#3b82f6","#ef4444","#84cc16","#f97316","#06b6d4"]
    for i, row in results.iterrows():
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            city  = row.get("city", f"Ville {i+1}")
            score = row.get("score_pct", 0)
            color = colors[int(row.get("rang", 1)-1) % len(colors)]
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=8 + (10 - min(row.get("rang",10),10)) * 1.2,
                color=color, fill=True, fill_color=color, fill_opacity=0.75,
                popup=folium.Popup(
                    f"<b>#{row['rang']} {city}</b><br>{row.get('cluster_label','')}<br>"
                    f"<b style='color:{color}'>{score:.0f}%</b> match<br>"
                    f"🌡️ {row.get('temp_avg',0):.1f}°C", max_width=180),
                tooltip=f"#{row['rang']} {city} — {score:.0f}%"
            ).add_to(m)
    return m


# ─────────────────────────────────────────────
#  ONGLET MON PROFIL
# ─────────────────────────────────────────────
def show_profile_tab(user: dict):
    tab_interests, tab_favs, tab_history = st.tabs([
        "⭐ Mes centres d'intérêt",
        "❤️ Mes favoris",
        "🕐 Historique"
    ])

    # ── CENTRES D'INTÉRÊT ────────────────────────────────────────
    with tab_interests:
        st.markdown("#### Modifiez vos centres d'intérêt")
        st.caption("Ces préférences sont utilisées dans toutes vos recherches.")

        current = get_user_interests(user["id"])

        fields = [
            ("nature",     "🌿 Nature & Randonnée"),
            ("patrimoine", "🏛️ Patrimoine & Histoire"),
            ("culture",    "🎭 Culture & Arts"),
            ("restaurant", "🍽️ Gastronomie"),
            ("nightlife",  "🎉 Vie nocturne"),
            ("loisirs",    "🎢 Loisirs"),
        ]

        cols = st.columns(3)
        new_interests = {}
        for i, (key, label) in enumerate(fields):
            with cols[i % 3]:
                val = st.slider(label, 1, 5,
                                value=int(current.get(key, 3)),
                                format="%d ⭐",
                                key=f"profile_{key}")
                stars = "★" * val + "☆" * (5 - val)
                st.markdown(f'<div style="color:#f59e0b;font-size:1.1rem">{stars}</div>',
                            unsafe_allow_html=True)
                new_interests[key] = val

        if st.button("💾 Sauvegarder mes centres d'intérêt", type="primary"):
            update_user_interests(user["id"], new_interests)
            # Mettre à jour la session
            st.session_state["user_interests"] = new_interests
            st.success("✅ Centres d'intérêt mis à jour !")
            st.rerun()

    # ── FAVORIS ──────────────────────────────────────────────────
    with tab_favs:
        favs = get_favorites(user["id"])
        if not favs:
            st.info("Aucune destination favorite. Lancez une recherche et cliquez sur 🤍 !")
        else:
            st.markdown(f"**{len(favs)} destination(s) sauvegardée(s)**")
            for fav in favs:
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f"**{fav['city']}** — {fav.get('country','')}")
                    st.caption(f"{fav.get('cluster_label','')} · {MONTH_NAMES.get(fav['month'], fav['month'])} · 🌡️ {fav.get('temp_avg',0):.1f}°C")
                with c2:
                    st.metric("Score", f"{fav['score_pct']:.0f}%")
                with c3:
                    if st.button("🗑️", key=f"del_fav_{fav['id']}"):
                        remove_favorite(user["id"], fav["city"], fav["month"])
                        st.rerun()
                st.divider()

    # ── HISTORIQUE ────────────────────────────────────────────────
    with tab_history:
        history = get_search_history(user["id"], limit=15)
        if not history:
            st.info("Aucune recherche effectuée.")
        else:
            for h in history:
                searched_at = h["searched_at"][:16].replace("T", " à ")
                with st.expander(f"📅 {searched_at} — Top : **{h['top_result']}** ({MONTH_NAMES.get(h['month'], h['month'])})"):
                    prefs = h["preferences"]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("🌡️ Température", f"{prefs.get('temp_avg','?')}°C")
                    with c2:
                        st.metric("🛡️ Confort", f"{prefs.get('indice_confort','?')}/100")
                    with c3:
                        st.metric("💰 Budget", prefs.get("budget_label", "?"))


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    init_db()

    if not is_logged_in():
        show_auth_page()
        return

    user = get_current_user()
    show_user_widget()

    # Charger les centres d'intérêt en session si pas encore fait
    if "user_interests" not in st.session_state:
        st.session_state["user_interests"] = get_user_interests(user["id"])

    page = st.session_state.get("page", "app")

    if page == "admin":
        if st.sidebar.button("← Retour à l'app", use_container_width=True):
            st.session_state["page"] = "app"
            st.rerun()
        show_admin_page(user)
        return


    user_interests = st.session_state["user_interests"]

    # ── SIDEBAR ──────────────────────────────────────────────────
    month, prefs, top_n, cluster_bonus = build_sidebar()

    # Fusionner les centres d'intérêt dans les prefs pour le moteur
    full_prefs = {**prefs, **user_interests}

    # ── HERO ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="hero-title">Votre destination<br><i>idéale</i> vous attend.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="hero-sub">Affinez vos critères dans la barre latérale — '
        'vos centres d\'intérêt sont déjà pris en compte.</div>',
        unsafe_allow_html=True
    )

    # ── CHARGEMENT DONNÉES ───────────────────────────────────────
    try:
        df = load_data(DATA_PATH)
    except FileNotFoundError:
        st.error(f"⚠️ Dataset introuvable : `{DATA_PATH}`")
        return

    # ___MAPPING___
    revenu_col = "Revenu moyen par habitant ($/jour)"

    # On définit les seuils basés sur la distribution réelle des données
    low_threshold = df[revenu_col].quantile(0.25)  # Les 25% les moins chers
    med_threshold = df[revenu_col].quantile(0.50)  # La médiane
    high_threshold = df[revenu_col].quantile(0.75) # Les 25% les plus chers


    # ── RECOMMANDATION ───────────────────────────────────────────
    with st.spinner(f"🔍 Recherche pour {MONTH_NAMES[month]}…"):
        results = recommend(
            df, month=month, user_prefs=full_prefs,
            top_n=top_n, cluster_bonus_id=cluster_bonus
        )

    if results.empty:
        st.error("Aucun résultat.")
        return

    # Sauvegarder la recherche
    city_col = "city" if "city" in results.columns else "ville"
    top_city = results.iloc[0].get(city_col, "?")
    save_search(user["id"], month, {**prefs, "budget_label": [k for k,v in BUDGET_MAP.items() if v == prefs.get("budget_pct")][0] if prefs.get("budget_pct") in BUDGET_MAP.values() else "?"}, top_city)

    # ── LAYOUT ───────────────────────────────────────────────────
    col_map, col_results = st.columns([3, 2], gap="large")

    with col_map:
        st.markdown(f"### 🗺️ Top {top_n} — {MONTH_NAMES[month]}")
        fmap = build_map(results)
        if fmap:
            st_folium(fmap, width=None, height=500)

        fig_bar = px.bar(
            results,
            x=city_col, y="score_pct",
            color="score_pct",
            color_continuous_scale=["#bae6fd", "#0ea5e9", "#0369a1"],
            labels={"score_pct": "Score (%)", city_col: ""},
            height=200,
        )
        fig_bar.update_layout(
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=10, b=30, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Outfit'),
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_results:
        st.markdown("### 🏆 Classement")

        for _, row in results.iterrows():
            city_name   = row.get(city_col, f"Ville #{row['rang']}")
            score       = row.get("score_pct", 0)
            cluster     = row.get("cluster_label", "")
            temp        = row.get("temp_avg", None)
            country     = row.get("country", "")
            already_fav = is_favorite(user["id"], city_name, month)

            with st.expander(
                f"#{row['rang']}  {city_name}  —  {score:.0f}%",
                expanded=row['rang'] <= 3
            ):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f'<div class="dest-rank">#{row["rang"]} match</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-name">{city_name}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-cluster">{cluster}</div>', unsafe_allow_html=True)
                    if temp is not None:
                        st.caption(f"🌡️ {temp:.1f}°C en {MONTH_NAMES[month]}")
                with c2:
                    st.markdown(f'<div class="dest-score">{score:.0f}%</div>', unsafe_allow_html=True)
                with c3:
                    fav_label = "❤️" if already_fav else "🤍"
                    if st.button(fav_label, key=f"fav_{row['rang']}_{city_name}",
                                 use_container_width=True,
                                 help="Retirer des favoris" if already_fav else "Ajouter aux favoris"):
                        if already_fav:
                            remove_favorite(user["id"], city_name, month)
                            st.toast(f"💔 {city_name} retiré des favoris")
                        else:
                            add_favorite(user["id"], city_name, country, month,
                                         score, float(temp) if temp else 0, cluster)
                            st.toast(f"❤️ {city_name} ajouté aux favoris !")
                        st.rerun()

                fig_radar = radar_chart(row, user_interests, city_name)
                st.plotly_chart(fig_radar, use_container_width=True,
                                key=f"radar_{row['rang']}")

                city_pics = get_cached_images(city_name, country)
                display_image_carousel(city_pics)

                description = row.get('short_description', "Aucune description disponible pour cette destination.")
                st.markdown(f"**À propos :** *{description}*")

    # ── TABLEAU COMPARATIF ───────────────────────────────────────
    st.markdown("---")
    display_cols = [city_col, "score_pct", "temp_avg", "cluster_label",
                    "nature", "culture", "nightlife", "indice_confort", "indice_securite"]
    display_cols = [c for c in display_cols if c in results.columns]
    rename_map = {
        "score_pct": "Score (%)", "temp_avg": "Temp. (°C)",
        "cluster_label": "Type", "nature": "Nature",
        "culture": "Culture", "nightlife": "Nightlife",
        "indice_confort": "Confort", "indice_securite": "Sécurité",
        city_col: "Ville"
    }
    st.markdown("### 📋 Comparatif")
    st.dataframe(
        results[display_cols].rename(columns=rename_map).round(1)
        .style.background_gradient(subset=["Score (%)"], cmap="Blues"),
        use_container_width=True, hide_index=True
    )

    # ── MON PROFIL ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 👤 Mon profil")
    show_profile_tab(user)


if __name__ == "__main__":
    main()