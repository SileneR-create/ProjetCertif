import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

@st.cache_data(ttl=86400)
def get_cached_images(city_name, country_name):
    """Récupère les URLs des images depuis Pexels avec mise en cache."""
    if not PEXELS_API_KEY:
        return []

    query = f"{city_name} {country_name}"
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=3&orientation=landscape"
    headers = {"Authorization": PEXELS_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [img['src']['large'] for img in data.get('photos', [])]
    except Exception:
        return []

def display_image_carousel(images):
    """Affiche un carrousel horizontal simple en HTML/CSS."""
    if not images:
        return

    html_code = f"""
    <div style="display: flex; overflow-x: auto; gap: 10px; padding: 10px; scroll-snap-type: x mandatory; margin-bottom: 20px;">
        {"".join(
            [f'<img src="{url}" style="height: 180px; border-radius: 12px; scroll-snap-align: start; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">' for url in images]
            )}
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


