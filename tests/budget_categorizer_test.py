"""
Script de test - Budget Categories
Lance ce script pour voir comment les catégories seraient créées sur vos données réelles
"""
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath("frontend"))

from budget_categorizer import BudgetCategorizer, display_budget_categories


def test_budget_categories():
    """
    Test la catégorisation de budget sur votre dataset
    """
    
    # À adapter : chemin vers votre fichier data_clean.csv
    CSV_PATH = r"..\DATA\processed\data_clean.csv"
    
    print("📂 Chargement du fichier CSV...")
    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {CSV_PATH}")
        print("   Veuillez modifier le chemin CSV_PATH dans ce script")
        return
    
    print(f"✓ Données chargées: {len(df)} villes\n")
    
    # Afficher les colonnes disponibles
    print("Colonnes disponibles:")
    for col in df.columns:
        print(f"  • {col}")
    print()
    
    # Tester avec 4 catégories
    print("\n" + "="*70)
    print("TEST 1: 4 CATÉGORIES")
    print("="*70)
    categorizer_4 = display_budget_categories(df, n_categories=4)
    
    # Afficher un exemple de catégorisation
    print("\nExemples de villes par catégorie:")
    for i, city in enumerate(categorizer_4.df["city"].head(10)):
        score = categorizer_4.df[categorizer_4.df["city"] == city]["budget_score"].values[0]
        category = categorizer_4.categorize_city(score)
        print(f"  {city:20s} → {category}")
    
    # Tester avec 3 catégories
    print("\n" + "="*70)
    print("TEST 2: 3 CATÉGORIES")
    print("="*70)
    categorizer_3 = display_budget_categories(df, n_categories=3)
    
    # Tester avec 5 catégories
    print("\n" + "="*70)
    print("TEST 3: 5 CATÉGORIES")
    print("="*70)
    categorizer_5 = display_budget_categories(df, n_categories=5)
    
    # Afficher les seuils pour filtrage
    print("\n" + "="*70)
    print("THRESHOLDS DE FILTRAGE (pour utiliser dans le moteur)")
    print("="*70)
    print("\nAvec 4 catégories:")
    for cat_name in categorizer_4.category_names:
        min_score, max_score = categorizer_4.get_category_threshold_for_filtering(cat_name)
        print(f"  {cat_name:30s}: {min_score:.3f} - {max_score:.3f}")
    
    # Afficher les percentiles réels calculés
    print("\n" + "="*70)
    print("PERCENTILES RÉELS (debug)")
    print("="*70)
    print(f"Budget score min: {categorizer_4.df['budget_score'].min():.3f}")
    print(f"Budget score max: {categorizer_4.df['budget_score'].max():.3f}")
    print(f"\nPercentiles calculés (seuils):")
    for i, threshold in enumerate(categorizer_4.thresholds):
        print(f"  Seuil {i}: {threshold:.3f}")


if __name__ == "__main__":
    test_budget_categories()