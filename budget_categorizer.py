"""
Budget Categorizer v2 - VERSION SIMPLIFIÉE
Basé UNIQUEMENT sur "Revenu moyen par habitant ($/jour)"
Plus stable, plus transparent, meilleure distribution
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


class BudgetCategorizer:
    """
    Crée des catégories de budget basées sur le revenu moyen par habitant.
    Simple, transparent, et bien distribuées.
    """

    def __init__(self, df: pd.DataFrame, n_categories: int = 4):
        """
        Initialise le catégoriseur

        Args:
            df: DataFrame avec colonne "Revenu moyen par habitant ($/jour)"
            n_categories: 3, 4, ou 5 (nombre de catégories à créer)
        """
        self.df = df.copy()
        self.n_categories = n_categories
        self.revenu_col = "Revenu moyen par habitant ($/jour)"

        # Nettoyer les données (remplacer NaN par la médiane)
        self.df[self.revenu_col] = self.df[self.revenu_col].fillna(self.df[self.revenu_col].median())

        # Le "score" est juste le revenu (plus simple !)
        self.df["budget_score"] = self.df[self.revenu_col]

        # Calculer les seuils et catégories
        self.thresholds = None
        self.categories = None
        self._compute_thresholds()

    def _compute_thresholds(self):
        """Calcule les seuils de budget basés sur les percentiles du revenu"""
        if self.n_categories == 3:
            percentiles = [0, 33.33, 66.67, 100]
            names = ["🎒 Budget serré", "💼 Moyen", "💎 Premium"]
        elif self.n_categories == 4:
            percentiles = [0, 25, 50, 75, 100]
            names = ["🎒 Budget serré", "✈️ Moyen", "🏨 Confortable", "💎 Luxe"]
        elif self.n_categories == 5:
            percentiles = [0, 20, 40, 60, 80, 100]
            names = ["🎒 Budget serré", "✈️ Économique", "💼 Moyen", "🏨 Confortable", "💎 Luxe"]
        else:
            raise ValueError("n_categories doit être 3, 4 ou 5")

        # Calculer les seuils basés sur les percentiles réels du revenu
        thresholds = []
        for i in range(len(percentiles) - 1):
            p_high = percentiles[i + 1]
            threshold = self.df[self.revenu_col].quantile(p_high / 100)
            thresholds.append(threshold)

        self.thresholds = thresholds[:-1]  # On garde n-1 seuils
        self.categories = {name: i for i, name in enumerate(names)}
        self.category_names = names

        return self

    def get_budget_map(self) -> Dict[str, int]:
        """
        Retourne le mapping catégorie -> indice numérique
        Exemple: {"🎒 Budget serré": 0, "✈️ Moyen": 1, ...}
        """
        return self.categories

    def get_category_info(self) -> Dict[str, Dict]:
        """
        Retourne les infos détaillées pour chaque catégorie
        Inclut les plages de revenu min/max réelles
        """
        info = {}

        for i, name in enumerate(self.category_names):
            # Trouver les destinations dans cette catégorie
            if i == 0:
                mask = self.df["budget_score"] <= self.thresholds[0]
            elif i == len(self.category_names) - 1:
                mask = self.df["budget_score"] > self.thresholds[i - 1]
            else:
                mask = (self.df["budget_score"] > self.thresholds[i - 1]) & (
                    self.df["budget_score"] <= self.thresholds[i]
                )

            cities_in_category = self.df[mask]

            info[name] = {
                "category_index": i,
                "num_cities": len(cities_in_category),
                "revenu_min": cities_in_category[self.revenu_col].min(),
                "revenu_max": cities_in_category[self.revenu_col].max(),
                "revenu_median": cities_in_category[self.revenu_col].median(),
                "revenu_mean": cities_in_category[self.revenu_col].mean(),
            }

        return info

    def categorize_city(self, revenu_score: float) -> str:
        """Détermine la catégorie d'une ville basée sur son revenu"""
        for i, threshold in enumerate(self.thresholds):
            if revenu_score <= threshold:
                return self.category_names[i]
        return self.category_names[-1]

    def get_category_threshold_for_filtering(self, category_name: str) -> Tuple[float, float]:
        """
        Retourne les seuils (min, max) de revenu pour une catégorie donnée
        Utile pour filtrer les destinations
        """
        category_idx = self.categories[category_name]

        if category_idx == 0:
            min_revenu = 0
        else:
            min_revenu = self.thresholds[category_idx - 1]

        if category_idx == len(self.category_names) - 1:
            max_revenu = float("inf")
        else:
            max_revenu = self.thresholds[category_idx]

        return (min_revenu, max_revenu)


def display_budget_categories(df: pd.DataFrame, n_categories: int = 4) -> BudgetCategorizer:
    """
    Fonction utilitaire pour afficher les catégories et les statistiques
    """
    categorizer = BudgetCategorizer(df, n_categories)

    print(f"\n{'='*70}")
    print(f"BUDGET CATEGORIES (n={n_categories})")
    print(f"{'='*70}\n")

    info = categorizer.get_category_info()

    for category_name, details in info.items():
        print(f"{category_name}")
        print(f"  • Nombre de villes: {details['num_cities']}")
        print(f"  • Revenu: ${details['revenu_min']:.2f} - ${details['revenu_max']:.2f}/jour")
        print(f"  • Médiane: ${details['revenu_median']:.2f}/jour")
        print(f"  • Moyenne: ${details['revenu_mean']:.2f}/jour")
        print()

    return categorizer
