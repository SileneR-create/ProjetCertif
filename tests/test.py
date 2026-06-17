"""
Test rapide - VERSION SIMPLIFIÉE
"""

import sys
import os
import pandas as pd

sys.path.append(os.path.abspath("../frontend"))
from budget_categorizer import display_budget_categories

CSV_PATH = r"..\DATA\processed\data_clean.csv"

print("📂 Chargement du fichier CSV...")
df = pd.read_csv(CSV_PATH)
print(f"✓ Données chargées: {len(df)} villes\n")

# Tester avec 4 catégories
print("=" * 70)
print("VERSION SIMPLIFIÉE - 4 CATÉGORIES")
print("=" * 70)
categorizer = display_budget_categories(df, n_categories=4)

# Montrer quelques exemples
print("\nExemples de villes:")
sample_cities = df["city"].unique()[:15]
for city in sample_cities:
    revenu = df[df["city"] == city][categorizer.revenu_col].iloc[0]
    category = categorizer.categorize_city(revenu)
    print(f"  {city:20s} (${revenu:6.2f}/jour) → {category}")

print("\n" + "=" * 70)
print("DISTRIBUTION PAR CATÉGORIE")
print("=" * 70)
info = categorizer.get_category_info()
total = sum([details["num_cities"] for details in info.values()])
for category_name, details in info.items():
    pct = (details["num_cities"] / total) * 100
    print(f"{category_name:30s}: {details['num_cities']:3d} villes ({pct:5.1f}%)")
