import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
from recommender import (
    recommend, engineer_features, MONTH_NAMES,
    ACTIVITY_FEATURES, COMFORT_FEATURES, ECONOMIC_FEATURES
)

# ─────────────────────────────────────────────
#  CONFIG PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TravelMatch · Trouvez votre destination idéale",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS CUSTOM
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Header principal */
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    color: #1a1a2e;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.hero-sub {
    font-size: 1.1rem;
    color: #64748b;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* Cards résultats */
.dest-card {
    background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%);
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    border-left: 4px solid #6366f1;
    transition: box-shadow 0.2s;
}
.dest-card:hover { box-shadow: 0 4px 20px rgba(99,102,241,0.15); }
.dest-rank { font-size: 0.8rem; color: #6366f1; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.dest-name { font-family: 'DM Serif Display', serif; font-size: 1.5rem; color: #1a1a2e; }
.dest-score { font-size: 2rem; font-weight: 600; color: #6366f1; }
.dest-cluster { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }

/* Sidebar */
.sidebar-section {
    font-family: 'DM Serif Display', serif;
    font-size: 1rem;
    color: #1a1a2e;
    border-bottom: 2px solid #6366f1;
    padding-bottom: 0.3rem;
    margin: 1.2rem 0 0.8rem 0;
}

/* Score bar */
.score-bar-bg {
    background: #e2e8f0;
    border-radius: 8px;
    height: 8px;
    margin-top: 6px;
}
.score-bar-fill {
    background: linear-gradient(90deg, #6366f1, #a855f7);
    border-radius: 8px;
    height: 8px;
}

/* Metric pills */
.metric-pill {
    display: inline-block;
    background: #f1f5f9;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.78rem;
    color: #475569;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CHARGEMENT DONNÉES
# ─────────────────────────────────────────────
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = engineer_features(df)
    return df


# ─────────────────────────────────────────────
#  SIDEBAR — PRÉFÉRENCES UTILISATEUR
# ─────────────────────────────────────────────
def build_sidebar():
    st.sidebar.markdown("## ✈️ TravelMatch")
    st.sidebar.markdown("*Définissez vos envies, on trouve votre destination.*")
    st.sidebar.markdown("---")

    prefs = {}

    # Mois
    st.sidebar.markdown('<div class="sidebar-section">🗓️ Période de voyage</div>', unsafe_allow_html=True)
    month_name = st.sidebar.selectbox("Mois de départ", list(MONTH_NAMES.values()), index=6)
    month = [k for k, v in MONTH_NAMES.items() if v == month_name][0]

    # Climat
    st.sidebar.markdown('<div class="sidebar-section">🌡️ Climat souhaité</div>', unsafe_allow_html=True)
    prefs["temp_avg"] = st.sidebar.slider("Température moyenne (°C)", -10, 40, 22)
    st.sidebar.caption(f"Je veux environ {prefs['temp_avg']}°C")

    # Activités
    st.sidebar.markdown('<div class="sidebar-section">🎯 Mes centres d\'intérêt</div>', unsafe_allow_html=True)
    activity_labels = {
        "nature": "🌿 Nature & Randonnée",
        "patrimoine": "🏛️ Patrimoine & Histoire",
        "culture": "🎭 Culture & Arts",
        "restaurant": "🍽️ Gastronomie",
        "nightlife": "🎉 Vie nocturne",
        "loisirs": "🎢 Loisirs & Activités",
    }
    for key, label in activity_labels.items():
        prefs[key] = st.sidebar.slider(label, 0, 5, 3)

    # Confort & Sécurité
    st.sidebar.markdown('<div class="sidebar-section">🛡️ Confort & Sécurité</div>', unsafe_allow_html=True)
    prefs["indice_confort"] = st.sidebar.slider("Niveau de confort sanitaire", 0, 100, 70)
    prefs["indice_securite"] = st.sidebar.slider("Niveau de sécurité / richesse", 0, 100, 60)

    # Tourisme
    st.sidebar.markdown('<div class="sidebar-section">🌍 Type de destination</div>', unsafe_allow_html=True)
    prefs["indice_tourisme"] = st.sidebar.slider("Popularité touristique", 0, 100, 50)
    prefs["valeur"] = st.sidebar.slider("Score général de la ville", 0, 10, 7)

    # Nombre de résultats
    st.sidebar.markdown("---")
    top_n = st.sidebar.number_input("Nombre de destinations", min_value=3, max_value=20, value=10)

    return month, prefs, top_n


# ─────────────────────────────────────────────
#  RADAR CHART
# ─────────────────────────────────────────────
def radar_chart(city_row: pd.Series, user_prefs: dict, city_name: str):
    categories = ["Nature", "Patrimoine", "Culture", "Restaurant", "Nightlife", "Loisirs"]
    keys = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]

    city_vals = [float(city_row.get(k, 0)) for k in keys]
    user_vals = [float(user_prefs.get(k, 0)) for k in keys]

    fig = go.Figure()

    # Ville EN PREMIER (en dessous)
    fig.add_trace(go.Scatterpolar(
        r=city_vals + [city_vals[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name=city_name,
        fillcolor='rgba(99,102,241,0.35)',
        line=dict(color='#6366f1', width=3),
    ))

    # Utilisateur PAR DESSUS (contour seulement, pas de fill opaque)
    fig.add_trace(go.Scatterpolar(
        r=user_vals + [user_vals[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='Vos envies',
        fillcolor='rgba(168,85,247,0.0)',   # transparent
        line=dict(color='#a855f7', width=2, dash='dash'),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
                tickfont=dict(size=9),
            )
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        height=300,
        margin=dict(t=20, b=40, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans'),
    )
    return fig


# ─────────────────────────────────────────────
#  CARTE FOLIUM
# ─────────────────────────────────────────────
def build_map(results: pd.DataFrame):
    if "latitude" not in results.columns or "longitude" not in results.columns:
        return None

    center_lat = results["latitude"].mean()
    center_lon = results["longitude"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=2,
                   tiles="CartoDB positron")

    colors = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981",
              "#3b82f6", "#ef4444", "#84cc16", "#f97316", "#06b6d4"]

    for i, row in results.iterrows():
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            city = row.get("city", row.get("ville", f"Ville {i+1}"))
            score = row.get("score_pct", 0)
            cluster_label = row.get("cluster_label", "")
            color = colors[i % len(colors)]

            popup_html = f"""
            <div style="font-family: DM Sans, sans-serif; min-width:180px">
                <div style="font-size:1.1rem; font-weight:600; color:{color}">#{row['rang']} {city}</div>
                <div style="font-size:0.85rem; color:#64748b; margin:4px 0">{cluster_label}</div>
                <div style="background:{color}22; border-radius:8px; padding:6px; margin-top:6px">
                    <span style="font-size:1.3rem; font-weight:700; color:{color}">{score:.0f}%</span>
                    <span style="font-size:0.75rem; color:#64748b"> de match</span>
                </div>
                <div style="font-size:0.78rem; color:#475569; margin-top:6px">
                    🌡️ {row.get('temp_avg', 'N/A'):.1f}°C
                </div>
            </div>
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=10 + (10 - i) * 1.2,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"#{row['rang']} {city} — {score:.0f}%",
            ).add_to(m)

    return m


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    month, user_prefs, top_n = build_sidebar()

    # ── HERO ──
    st.markdown('<div class="hero-title">Votre destination<br><i>idéale</i> vous attend.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Ajustez vos critères dans la barre latérale, et laissez l\'IA trouver les villes qui vous correspondent.</div>', unsafe_allow_html=True)

    # ── CHARGEMENT ──
    data_file = st.text_input("📂 Chemin vers votre dataset CSV", value="DATA/processed/data_clean.csv", key="data_path")

    try:
        df = load_data(data_file)
    except FileNotFoundError:
        st.warning("⚠️ Dataset introuvable. Chargez votre fichier CSV ci-dessus ou placez `data.csv` dans le même dossier.")
        st.info("💡 Structure attendue : colonnes `month`, `temp_avg`, `nature`, `culture`, `latitude`, `longitude`…")
        _show_demo_mode()
        return

    # ── RECOMMANDATION ──
    with st.spinner(f"🔍 Analyse des destinations pour {MONTH_NAMES[month]}…"):
        results = recommend(df, month=month, user_prefs=user_prefs, top_n=top_n)

    if results.empty:
        st.error("Aucun résultat pour ces critères.")
        return

    # ── LAYOUT PRINCIPAL ──
    col_map, col_results = st.columns([3, 2], gap="large")

    # CARTE
    with col_map:
        st.markdown(f"### 🗺️ Top {top_n} destinations — {MONTH_NAMES[month]}")
        fmap = build_map(results)
        if fmap:
            st_folium(fmap, width=None, height=520)
        else:
            st.info("Ajoutez les colonnes `latitude` et `longitude` pour afficher la carte.")

        # Distribution des scores
        fig_bar = px.bar(
            results,
            x=results.get("city", results.get("ville", results.index)).values if "city" in results.columns or "ville" in results.columns else results.index,
            y="score_pct",
            color="score_pct",
            color_continuous_scale=["#e0e7ff", "#6366f1", "#4f46e5"],
            labels={"y": "Score de match (%)", "x": "Ville"},
            height=220,
        )
        fig_bar.update_layout(
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=10, b=40, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='DM Sans'),
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    # LISTE RÉSULTATS
    with col_results:
        st.markdown("### 🏆 Classement")
        city_col = "city" if "city" in results.columns else ("ville" if "ville" in results.columns else None)

        for _, row in results.iterrows():
            city_name = row[city_col] if city_col else f"Ville #{row['rang']}"
            score = row.get("score_pct", 0)
            cluster = row.get("cluster_label", "")
            temp = row.get("temp_avg", None)

            print(f"DEBUG {city_name} — ville: {[float(row.get(k, 0)) for k in ['nature','patrimoine','culture','restaurant','nightlife','loisirs']]}")
            print(f"DEBUG user — {[user_prefs.get(k, 0) for k in ['nature','patrimoine','culture','restaurant','nightlife','loisirs']]}")

            with st.expander(f"#{row['rang']}  {city_name}  —  {score:.0f}%", expanded=row['rang'] <= 3):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f'<div class="dest-rank">#{row["rang"]} match</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-name">{city_name}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="dest-cluster">{cluster}</div>', unsafe_allow_html=True)
                    if temp is not None:
                        st.caption(f"🌡️ {temp:.1f}°C en {MONTH_NAMES[month]}")
                with c2:
                    st.markdown(f'<div class="dest-score">{score:.0f}%</div>', unsafe_allow_html=True)

                # Radar
                fig_radar = radar_chart(row, user_prefs, city_name)
                st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_{row['rang']}")

    # ── TABLEAU COMPARATIF ──
    st.markdown("---")
    st.markdown("### 📋 Tableau comparatif")
    display_cols = [city_col, "score_pct", "temp_avg", "cluster_label",
                    "nature", "culture", "nightlife", "indice_confort", "indice_securite"]
    display_cols = [c for c in display_cols if c and c in results.columns]
    rename_map = {
        "score_pct": "Score (%)", "temp_avg": "Temp. moy. (°C)",
        "cluster_label": "Type", "nature": "Nature", "culture": "Culture",
        "nightlife": "Nightlife", "indice_confort": "Confort",
        "indice_securite": "Sécurité", city_col: "Ville"
    }
    df_display = results[display_cols].rename(columns=rename_map)
    df_display = df_display.round(1)
    st.dataframe(
        df_display.style.background_gradient(subset=["Score (%)"], cmap="BuPu"),
        use_container_width=True, hide_index=True
    )


def _show_demo_mode():
    """Affiche une interface de démonstration sans données."""
    st.markdown("---")
    st.markdown("#### 🎮 Mode démonstration")
    st.markdown("""
    **Structure CSV attendue :**
    ```
    city, country, month, latitude, longitude,
    temp_avg, temp_max, temp_min,
    nature, patrimoine, culture, restaurant, nightlife, loisirs,
    valeur, PIB par habitant (USD), Accès eau potable (% pop), ...
    ```
    Placez votre fichier `data.csv` dans le même répertoire que `app.py` et relancez.
    """)


if __name__ == "__main__":
    main()