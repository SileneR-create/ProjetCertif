"""
Tests de qualité des données — TravelMatch
C12 — Valider les jeux de données : structure, complétude, cohérence.

Vérifie que le fichier data_clean.csv produit par le pipeline ETL
respecte le contrat de données attendu par le moteur de recommandation ML.
Ces tests passent en CI (fichier présent dans le dépôt) et se sautent
automatiquement si le fichier est absent en environnement local.
"""

import os
import pytest
import pandas as pd

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "DATA", "processed", "data_clean.csv",
)

ACTIVITY_FEATURES = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]

CRITICAL_COLUMNS = ["city", "month", "temp_avg"] + ACTIVITY_FEATURES


# ── FIXTURE ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def df():
    if not os.path.exists(DATA_PATH):
        pytest.skip(f"Fichier de données introuvable : {DATA_PATH}")
    return pd.read_csv(DATA_PATH)


# ── EXISTENCE & ACCESSIBILITÉ ────────────────────────────────────────────────

def test_data_file_exists():
    """C12 — Le fichier data_clean.csv produit par l'ETL doit exister."""
    assert os.path.exists(DATA_PATH), (
        f"Fichier manquant : {DATA_PATH}\n"
        "Lancez le pipeline ETL avant d'exécuter les tests."
    )


def test_file_is_readable(df):
    """C12 — Le fichier doit être lisible et non vide."""
    assert df is not None
    assert len(df) > 0, "Le fichier data_clean.csv est vide."


# ── STRUCTURE DES COLONNES ────────────────────────────────────────────────────

def test_required_columns_present(df):
    """C12 — Toutes les colonnes critiques pour le moteur ML doivent être présentes."""
    missing = [col for col in CRITICAL_COLUMNS if col not in df.columns]
    assert not missing, (
        f"Colonnes manquantes dans data_clean.csv : {missing}\n"
        "Ces colonnes sont requises par le moteur de recommandation KMeans/RandomForest."
    )


# ── VOLUMÉTRIE ────────────────────────────────────────────────────────────────

def test_minimum_row_count(df):
    """C12 — Le dataset doit contenir au moins 100 lignes (destinations × mois)."""
    assert len(df) >= 100, (
        f"Dataset trop petit : {len(df)} lignes. "
        "Vérifiez que le pipeline ETL a bien chargé toutes les sources."
    )


def test_at_least_six_distinct_cities(df):
    """Le modèle KMeans (n_clusters=6) requiert au moins 6 villes distinctes."""
    if "city" not in df.columns:
        pytest.skip("Colonne 'city' absente")
    n = df["city"].nunique()
    assert n >= 6, (
        f"Seulement {n} villes distinctes. "
        "KMeans(n_clusters=6) échouera si n_samples < n_clusters."
    )


# ── COMPLÉTUDE DES DONNÉES ────────────────────────────────────────────────────

def test_no_null_in_activity_features(df):
    """C12 — Les features d'activité ne doivent contenir aucune valeur nulle."""
    for col in ACTIVITY_FEATURES:
        if col not in df.columns:
            continue
        null_count = int(df[col].isna().sum())
        assert null_count == 0, (
            f"Colonne '{col}' : {null_count} valeur(s) NULL détectée(s). "
            "Le pipeline ETL doit imputer les manquants avant stockage."
        )


# ── COHÉRENCE DES VALEURS ─────────────────────────────────────────────────────

def test_activity_features_in_range_0_100(df):
    """Les features d'activité doivent être dans la plage attendue [0, 100]."""
    for col in ACTIVITY_FEATURES:
        if col not in df.columns:
            continue
        out = df[(df[col] < 0) | (df[col] > 100)]
        assert len(out) == 0, (
            f"Colonne '{col}' : {len(out)} valeur(s) hors de [0, 100] "
            f"(min={df[col].min():.1f}, max={df[col].max():.1f})."
        )


def test_month_values_are_valid(df):
    """La colonne 'month' doit contenir uniquement des entiers de 1 à 12."""
    if "month" not in df.columns:
        pytest.skip("Colonne 'month' absente")
    invalid = df[~df["month"].between(1, 12)]
    assert len(invalid) == 0, (
        f"{len(invalid)} ligne(s) avec un mois invalide. "
        f"Valeurs présentes : {sorted(df['month'].unique().tolist())}"
    )


def test_temperature_in_realistic_range(df):
    """La température moyenne annuelle doit rester dans [-30, 55] °C."""
    if "temp_avg" not in df.columns:
        pytest.skip("Colonne 'temp_avg' absente")
    numeric_temp = pd.to_numeric(df["temp_avg"], errors="coerce")
    out = numeric_temp[(numeric_temp < -30) | (numeric_temp > 55)]
    assert len(out) == 0, (
        f"{len(out)} valeur(s) de température hors de [-30, 55]°C. "
        "Vérifiez le pipeline de nettoyage des données météo."
    )
