import streamlit as st  # type: ignore
import pandas as pd
import plotly.graph_objects as go  # type: ignore
import plotly.express as px  # type: ignore
import folium  # type: ignore
from streamlit_folium import st_folium  # type: ignore
import sys
import os
import requests

# Configuration du chemin racine (conservée pour charger les outils visuels si nécessaire)
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from frontend.admin import show_admin_page
from frontend.auth import show_user_widget, is_logged_in, get_current_user
from backend.utils import get_cached_images, display_image_carousel

# ── CONFIGURATION DE L'URL DE L'API ──
API_URL = os.getenv("API_URL", "http://localhost:8000")

MONTH_NAMES = {
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

# ─────────────────────────────────────────────
#  CONFIG PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TravelMatch",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
#  PAGE INSCRIPTION & CONNEXION
# ─────────────────────────────────────────────
def show_auth_page():
    st.markdown(
        """
    <div style="text-align:center; padding: 2rem 0 1rem;">
        <div style="font-family:'Playfair Display',serif; font-size:3rem; color:#0f172a;">✈️ TravelMatch</div>
        <div style="color:#64748b; font-size:1rem; font-weight:300;">
            Votre destination idéale, calculée sur mesure.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["🔑 Connexion", "📝 Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            st.markdown("#### Bon retour 👋")
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Remplissez tous les champs.")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/login", json={"username": username, "password": password}
                        )
                        if response.status_code == 200:
                            st.session_state["user"] = response.json()["user"]
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Identifiants incorrects."))
                    except requests.exceptions.ConnectionError:
                        st.error("Impossible de joindre le backend FastAPI.")

    with tab_register:
        with st.form("register_form"):
            st.markdown("#### Créer mon compte")
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Nom d'utilisateur")
                new_password = st.text_input("Mot de passe", type="password")
            with c2:
                new_email = st.text_input("Email")
                new_password2 = st.text_input("Confirmer le mot de passe", type="password")

            st.markdown("---")
            st.markdown("#### 🎯 Vos centres d'intérêt")

            cols = st.columns(3)
            interests = {}
            fields = [
                ("nature", "🌿 Nature"),
                ("patrimoine", "🏛️ Patrimoine"),
                ("culture", "🎭 Culture"),
                ("restaurant", "🍽️ Gastronomie"),
                ("nightlife", "🎉 Nightlife"),
                ("loisirs", "🎢 Loisirs"),
            ]
            for i, (key, label) in enumerate(fields):
                with cols[i % 3]:
                    interests[key] = st.slider(label, 1, 5, 3, format="%d ⭐", key=f"reg_{key}")
                    stars = "★" * interests[key] + "☆" * (5 - interests[key])
                    st.markdown(f'<div style="color:#f59e0b;font-size:1.1rem">{stars}</div>', unsafe_allow_html=True)

            if st.form_submit_button("Créer mon compte ✈️", use_container_width=True, type="primary"):
                if not all([new_username, new_email, new_password, new_password2]):
                    st.error("Remplissez tous les champs.")
                elif new_password != new_password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_password) < 6:
                    st.error("Mot de passe trop court (min. 6 caractères).")
                else:
                    try:
                        payload = {
                            "username": new_username,
                            "email": new_email,
                            "password": new_password,
                            "interests": interests,
                        }
                        response = requests.post(f"{API_URL}/auth/register", json=payload)
                        if response.status_code == 200:
                            login_res = requests.post(
                                f"{API_URL}/auth/login", json={"username": new_username, "password": new_password}
                            )
                            st.session_state["user"] = login_res.json()["user"]
                            st.success("Compte créé ! Bienvenue 🎉")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Erreur d'inscription"))
                    except requests.exceptions.ConnectionError:
                        st.error("Serveur indisponible.")


@st.cache_data(ttl=300)
def _get_budget_info(api_url: str) -> dict:
    try:
        return requests.get(f"{api_url}/budget/info").json()
    except Exception:
        return {}


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
def build_sidebar():
    st.sidebar.markdown("## ✈️ TravelMatch")
    st.sidebar.markdown("*Affinez votre recherche*")
    st.sidebar.markdown("---")

    st.sidebar.markdown('<div class="sidebar-section">🗓️ Période</div>', unsafe_allow_html=True)
    month_name = st.sidebar.selectbox(
        "Mois du séjour", list(MONTH_NAMES.values()), index=st.session_state.get("month_index", 6), key="month_select"
    )
    month = [k for k, v in MONTH_NAMES.items() if v == month_name][0]

    st.sidebar.markdown('<div class="sidebar-section">🌡️ Climat</div>', unsafe_allow_html=True)
    temp_avg = st.sidebar.slider("Température souhaitée (°C)", -10, 40, key="temp_slider")

    st.sidebar.markdown('<div class="sidebar-section">🗺️ Type de destination</div>', unsafe_allow_html=True)
    cluster_options = {
        "Pas de préférence": None,
        "🌿 Nature & Aventure": 0,
        "🏛️ Patrimoine & Histoire": 1,
        "🎭 Culture & Arts": 2,
        "🌊 Détente & Plages": 3,
        "🏙️ Métropole Moderne": 4,
        "🎉 Fête & Nightlife": 5,
    }
    cluster_choice = st.sidebar.selectbox("Je cherche...", list(cluster_options.keys()), key="cluster_select")
    cluster_bonus = cluster_options[cluster_choice]

    st.sidebar.markdown('<div class="sidebar-section">🏗️ Accéssibilité</div>', unsafe_allow_html=True)
    indice_electricite = st.sidebar.slider("Électricité accessible (% pop)", 0, 100, 80, key="slider_electricite")
    indice_internet = st.sidebar.slider("Internet accessible (% pop)", 0, 100, 70, key="slider_internet")
    indice_eau = st.sidebar.slider("Eau potable accessible (% pop)", 0, 100, 85, key="slider_eau")
    indice_medecins = st.sidebar.slider("Médecins (pour 1000 habitants)", 0.0, 5.0, 2.0, key="slider_medecins")

    st.sidebar.markdown('<div class="sidebar-section">💰 Budget sur place</div>', unsafe_allow_html=True)
    budget_info = _get_budget_info(API_URL)

    budget_options = {}
    for category_name, details in budget_info.items():
        budget_options[f"{category_name} (~${details['revenu_median']:.0f}/jour, {details['num_cities']} villes)"] = (
            category_name
        )

    if not budget_options:
        budget_options = {
            "🎒 Budget serré": "🎒 Budget serré",
            "✈️ Moyen": "✈️ Moyen",
            "🏨 Confortable": "🏨 Confortable",
            "💎 Luxe": "💎 Luxe",
        }

    budget_label_with_info = st.sidebar.radio(
        "Niveau de vie du pays", list(budget_options.keys()), index=1, key="budget_radio"
    )
    budget_label = budget_options[budget_label_with_info]

    try:
        budget_val = requests.get(f"{API_URL}/budget/map-value", params={"label": budget_label}).json()
    except Exception:
        budget_val = 1

    st.sidebar.markdown("---")
    top_n = st.sidebar.number_input("Nombre de destinations", min_value=3, max_value=20, value=10)

    prefs = {
        "temp_avg": temp_avg,
        "indice_electricite": indice_electricite,
        "indice_internet": indice_internet,
        "indice_eau": indice_eau,
        "indice_medecins": indice_medecins,
        "budget_pct": budget_val,
        "budget_label": budget_label,
    }
    return month, prefs, top_n, cluster_bonus


# ─────────────────────────────────────────────
#  VISUELS GRAPHES & MAP
# ─────────────────────────────────────────────
def radar_chart(city_row: pd.Series, user_interests: dict, city_name: str):
    categories = ["Nature", "Patrimoine", "Culture", "Restaurant", "Nightlife", "Loisirs"]
    keys = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]
    city_vals = [float(city_row.get(k, 0)) for k in keys]
    user_vals = [float(user_interests.get(k, 0)) for k in keys]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=city_vals + [city_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=city_name,
            fillcolor="rgba(14,165,233,0.25)",
            line=dict(color="#0ea5e9", width=3),
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=user_vals + [user_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Vos envies",
            fillcolor="rgba(245,158,11,0.0)",
            line=dict(color="#f59e0b", width=2, dash="dash"),
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5], tickfont=dict(size=9))),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        height=300,
        margin=dict(t=20, b=40, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit"),
    )
    return fig


def build_map(results: pd.DataFrame, city_col: str):
    if "latitude" not in results.columns or "longitude" not in results.columns:
        return None
    m = folium.Map(
        location=[results["latitude"].mean(), results["longitude"].mean()], zoom_start=2, tiles="CartoDB positron"
    )
    colors = [
        "#0ea5e9",
        "#6366f1",
        "#ec4899",
        "#f59e0b",
        "#10b981",
        "#3b82f6",
        "#ef4444",
        "#84cc16",
        "#f97316",
        "#06b6d4",
    ]
    for i, row in results.iterrows():
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            city = row.get(city_col, f"Ville {i+1}")
            score = row.get("score_pct", 0)
            color = colors[int(row.get("rang", 1) - 1) % len(colors)]
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=8 + (10 - min(row.get("rang", 10), 10)) * 1.2,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                popup=folium.Popup(
                    f"<b>#{row['rang']} {city}</b><br>{row.get('cluster_label','')}<br><b style='color:{color}'>{score:.0f}%</b> match<br>🌡️ {row.get('temp_avg',0):.1f}°C",
                    max_width=180,
                ),
                tooltip=f"#{row['rang']} {city} — {score:.0f}%",
            ).add_to(m)
    return m


# ─────────────────────────────────────────────
#  ONGLET PROFIL COMPLET
# ─────────────────────────────────────────────
def show_profile_tab(user: dict):
    tab_interests, tab_favs, tab_history = st.tabs(["⭐ Mes centres d'intérêt", "❤️ Mes favoris", "🕐 Historique"])

    with tab_interests:
        st.markdown("#### Modifiez vos centres d'intérêt")
        try:
            current = requests.get(f"{API_URL}/users/{user['id']}/interests").json()
        except Exception:
            current = {}

        fields = [
            ("nature", "🌿 Nature & Randonnée"),
            ("patrimoine", "🏛️ Patrimoine & Histoire"),
            ("culture", "🎭 Culture & Arts"),
            ("restaurant", "🍽️ Gastronomie"),
            ("nightlife", "🎉 Vie nocturne"),
            ("loisirs", "🎢 Loisirs"),
        ]
        cols = st.columns(3)
        new_interests = {}
        for i, (key, label) in enumerate(fields):
            with cols[i % 3]:
                val = st.slider(label, 1, 5, value=int(current.get(key, 3)), format="%d ⭐", key=f"profile_{key}")
                stars = "★" * val + "☆" * (5 - val)
                st.markdown(f'<div style="color:#f59e0b;font-size:1.1rem">{stars}</div>', unsafe_allow_html=True)
                new_interests[key] = val

        if st.button("💾 Sauvegarder mes centres d'intérêt", type="primary"):
            requests.put(f"{API_URL}/users/{user['id']}/interests", json=new_interests)
            st.session_state["user_interests"] = new_interests
            st.success("✅ Centres d'intérêt mis à jour !")
            st.rerun()

    with tab_favs:
        try:
            favs = requests.get(f"{API_URL}/favorites", params={"user_id": user["id"]}).json()
        except Exception:
            favs = []

        if not favs:
            st.info("Aucune destination favorite. Lancez une recherche et cliquez sur 🤍 !")
        else:
            st.markdown(f"**{len(favs)} destination(s) sauvegardée(s)**")
            for fav in favs:
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f"**{fav['city']}** — {fav.get('country','')}")
                    st.caption(
                        f"{fav.get('cluster_label','')} · {MONTH_NAMES.get(int(fav['month']), fav['month'])} · 🌡️ {fav.get('temp_avg',0):.1f}°C"
                    )
                with c2:
                    st.metric("Score", f"{fav['score_pct']:.0f}%")
                with c3:
                    if st.button("🗑️", key=f"del_fav_{fav['id']}"):
                        requests.delete(
                            f"{API_URL}/favorites",
                            json={"user_id": user["id"], "city": fav["city"], "month": int(fav["month"])},
                        )
                        st.rerun()
                st.divider()

    with tab_history:
        try:
            history = requests.get(f"{API_URL}/history", params={"user_id": user["id"], "limit": 15}).json()
        except Exception:
            history = []

        if not history:
            st.info("Aucune recherche effectuée.")
        else:
            for h in history:
                searched_at = h["searched_at"][:16].replace("T", " à ")
                try:
                    m_idx = int(h["month"])
                    m_lbl = MONTH_NAMES.get(m_idx, h["month"])
                except ValueError:
                    m_lbl = h["month"]

                with st.expander(f"📅 {searched_at} — Top : **{h['top_result']}** ({m_lbl})"):
                    prefs_h = h["preferences"]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("🌡️ Température", f"{prefs_h.get('temp_avg','?')}°C")
                    with c2:
                        st.metric("🛡️ Confort", f"{prefs_h.get('indice_confort','?')}/100")
                    with c3:
                        st.metric("💰 Budget", prefs_h.get("budget_label", "?"))


# ─────────────────────────────────────────────
#  FONCTION PRINCIPALE (MAIN)
# ─────────────────────────────────────────────
def main():
    if not is_logged_in():
        show_auth_page()
        return

    user = get_current_user()
    show_user_widget()

    if "user_interests" not in st.session_state:
        try:
            st.session_state["user_interests"] = requests.get(f"{API_URL}/users/{user['id']}/interests").json()
        except Exception:
            st.session_state["user_interests"] = {
                "nature": 3,
                "patrimoine": 3,
                "culture": 3,
                "restaurant": 3,
                "nightlife": 3,
                "loisirs": 3,
            }

    if user and user.get("is_admin", 0) == 1:
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Modération")

        if st.session_state.get("page", "app") == "app":
            if st.sidebar.button("🛠️ Ouvrir le Panneau Admin", use_container_width=True, type="secondary"):
                st.session_state["page"] = "admin"
                st.rerun()

    page = st.session_state.get("page", "app")

    if page == "admin":
        if st.sidebar.button("← Retour à l'app", use_container_width=True, type="primary"):
            st.session_state["page"] = "app"
            st.rerun()

        show_admin_page()
        return

    user_interests = st.session_state["user_interests"]

    # Construction Sidebar
    month, prefs, top_n, cluster_bonus = build_sidebar()

    # Titres Visuels
    st.markdown('<div class="hero-title">Votre destination<br><i>idéale</i> vous attend.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Ajustez vos critères dans la barre latérale à gauche puis lancez la recherche.</div>',
        unsafe_allow_html=True,
    )

    # Initialisation de la structure des résultats
    results = pd.DataFrame()

    # ── LE BOUTON DE RECHERCHE ──
    if st.button("🔍 Lancer la recherche de destinations", type="primary", use_container_width=True):
        with st.spinner(f"🔍 Recherche pour {MONTH_NAMES[month]}…"):
            payload = {
                "month": month,
                "user_id": user["id"],
                "top_n": top_n,
                "cluster_bonus": cluster_bonus,
                "prefs": prefs,
            }
            try:
                response = requests.post(f"{API_URL}/recommendations", json=payload)
                if response.status_code == 200:
                    data_json = response.json()
                    results = pd.DataFrame(data_json)
                    # Sauvegarde en session pour persistance sur l'UI distant
                    st.session_state["last_results"] = data_json
                    st.session_state["last_month"] = month
                else:
                    st.error(f"Erreur du serveur : {response.json().get('detail', 'Inconnue')}")
                    return
            except requests.exceptions.ConnectionError:
                st.error("❌ Impossible de contacter le serveur FastAPI. Est-il démarré ?")
                return
    else:
        # Si aucun clic mais qu'une recherche a déjà eu lieu, on maintient l'affichage
        if "last_results" in st.session_state:
            results = pd.DataFrame(st.session_state["last_results"])
            month = st.session_state["last_month"]

    # État initial sans recherche
    if results.empty:
        st.info(
            "👋 Bienvenue ! Ajustez vos filtres à gauche, puis cliquez sur le bouton ci-dessus pour lancer votre recherche."
        )
        return

    # Détection dynamique du nom de colonne Ville
    city_col = "city" if "city" in results.columns else ("ville" if "ville" in results.columns else results.columns[0])

    # ── LAYOUT VISUEL (CARTE ET CLASSEMENT) ──
    col_map, col_results = st.columns([3, 2], gap="large")

    with col_map:
        st.markdown(f"### 🗺️ Top {top_n} — {MONTH_NAMES[month]}")
        fmap = build_map(results, city_col)
        if fmap:
            st_folium(fmap, width=None, height=500)

        fig_bar = px.bar(
            results,
            x=city_col,
            y="score_pct",
            color="score_pct",
            color_continuous_scale=["#bae6fd", "#0ea5e9", "#0369a1"],
            labels={"score_pct": "Score (%)", city_col: ""},
            height=200,
        )
        fig_bar.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(t=10, b=30, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_results:
        st.markdown("### 🏆 Classement")

        # Charge tous les favoris en une seule requête (évite N appels /favorites/check)
        try:
            user_favs = requests.get(f"{API_URL}/favorites", params={"user_id": user["id"]}).json()
            fav_set = {(f["city"], int(f["month"])) for f in user_favs}
        except Exception:
            fav_set = set()

        for _, row in results.iterrows():
            city_name = row.get(city_col, f"Ville #{row['rang']}")
            score = row.get("score_pct", 0)
            cluster = row.get("cluster_label", "")
            temp = row.get("temp_avg", None)
            dollars = row.get("Revenu moyen par habitant ($/jour)", None)
            country = row.get("country", "")

            already_fav = (city_name, month) in fav_set

            with st.expander(f"#{row['rang']}  {city_name}  —  {score:.0f}%", expanded=row["rang"] <= 3):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f'<div class="dest-rank">#{row["rang"]} match</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-name">{city_name}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-cluster">{cluster}</div>', unsafe_allow_html=True)
                    if temp is not None:
                        st.caption(f"🌡️ {temp:.1f}°C en {MONTH_NAMES[month]}")
                    if dollars is not None:
                        st.caption(f"💵 {dollars:.1f}$/jour")
                    st.markdown(f'<div class="dest-score">{score:.0f}%</div>', unsafe_allow_html=True)
                with c3:
                    fav_label = "❤️" if already_fav else "🤍"
                    if st.button(fav_label, key=f"fav_{row['rang']}_{city_name}", use_container_width=True):
                        if already_fav:
                            requests.delete(
                                f"{API_URL}/favorites", json={"user_id": user["id"], "city": city_name, "month": month}
                            )
                            st.toast(f"💔 {city_name} retiré des favoris")
                        else:
                            payload_fav = {
                                "user_id": user["id"],
                                "city": city_name,
                                "country": country,
                                "month": month,
                                "score_pct": float(score),
                                "temp_avg": float(temp) if temp else 0.0,
                                "cluster_label": cluster,
                            }
                            requests.post(f"{API_URL}/favorites", json=payload_fav)
                            st.toast(f"❤️ {city_name} ajouté aux favoris !")
                        st.rerun()

                fig_radar = radar_chart(row, user_interests, city_name)
                st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_{row['rang']}")

                city_pics = get_cached_images(city_name, country)
                display_image_carousel(city_pics)

                description = row.get("short_description", "Aucune description disponible pour cette destination.")
                st.markdown(f"**À propos :** *{description}*")

    # ── TABLEAU COMPARATIF ──
    st.markdown("---")
    display_cols = [
        city_col,
        "score_pct",
        "temp_avg",
        "cluster_label",
        "nature",
        "culture",
        "nightlife",
        "indice_confort",
        "indice_securite",
    ]
    display_cols = [c for c in display_cols if c in results.columns]
    rename_map = {
        "score_pct": "Score (%)",
        "temp_avg": "Temp. (°C)",
        "cluster_label": "Type",
        "nature": "Nature",
        "culture": "Culture",
        "nightlife": "Nightlife",
        "indice_confort": "Confort",
        "indice_securite": "Sécurité",
        city_col: "Ville",
    }

    st.markdown("### 📋 Comparatif")
    st.dataframe(
        results[display_cols]
        .rename(columns=rename_map)
        .round(1)
        .style.background_gradient(subset=["Score (%)"], cmap="Blues"),
        use_container_width=True,
        hide_index=True,
    )

    # ── PROFIL GLOBAL ──
    st.markdown("---")
    st.markdown("### 👤 Mon profil")
    show_profile_tab(user)


if __name__ == "__main__":
    main()
