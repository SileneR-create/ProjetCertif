Mon projet est une application basée sur le machine learning qui analyse le profil des voyageurs pour recommander des destinations adaptées. Elle prend en compte les préférences, le budget et le style de voyage. Elle permet aussi d’identifier des destinations sous-cotées, moins connues mais intéressantes.

# **“Direction” des données**

## MCD

[mcd_merise_travel_recommender_v2.html](attachment:ef9b46ed-b1a7-4299-9356-0f64d5af8720:mcd_merise_travel_recommender_v2.html)

## MPD

### Base de données

<aside>
🗄️

## ***BDD_Projet_Certif***

- Activites
    - id_activite
    - nom_activite
    - categorie
- activite_destination
    - id_destination
    - id_activite
- Destination
    - id_destination
    - pays
    - ville
    - code_iso3
    - continent
    - type_climat
    - latitude
    - longitude
- indicateurs_WorldBank
    - id_worldbank INTEGER PRIMARY KEY
    - code_indicateur TEXT
    - libele TEXT,
    - categorie TEXT,
    - valeur INTEGER,
    - annee INTEGER,
    - date_import DATE
    - id_destination INTEGER,
- preference_activites
    - priorite TEXT,
    - id_user INTEGER,
    - id_activite INTEGER,
- Profils_voyageurs
    - id_profil INTEGER PRIMARY KEY AUTOINCREMENT
    - budget INTEGER,
    - niveau_confort INTEGER
    - durée_voyage_jour INTEGER,
    - nb_voyageur INTEGER,
    - climat_souhaite TEXT,
    - id_user INTEGER,
- Recommandations
    - id_recommandation INTEGER PRIMARY KEY AUTOINCREMENT,
    - score_matching INTEGER,
    - score_budget INTEGER
    - score_activité INTEGER,
    - score_securite INTEGER,
    - score_climat INTEGER,
    - date_generation DATE
    - id_user INTEGER,
    - id_destination INTEGER,
- Saisonnalites
    - id_saisonnalite INTEGER PRIMARY KEY AUTOINCREMENT
    - mois INTEGER
    - condition_meteo TEXT,
    - temps_moy_celsius INTEGER,
    - precipitation_mm INTEGER,
    - recommandation TEXT,
    - id_destination INTEGER,
- Users
    - id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    - nom_user TEXT
</aside>

# **Récupération de données**

## CSV- Kaggle

- **Travel Destinations**

[Travel Destinations](https://www.kaggle.com/datasets/leondesilva1/travel-destinations)

> Le jeu de données contient des villes, le pays auquel elles appartiennent, des catégories ainsi que les meilleures périodes pour voyager. Cela peut être utile pour simuler un ensemble de données indiquant où voyager, quand voyager et quel type d’expérience vivre.
> 

<aside>
❗

Faute d’intérêts supplémentaire à la 2eme base de données plus complète, **je n’ai pas exploité celle-ci**

</aside>

- **Worldwide Travel Cities**

[Worldwide Travel Cities (Ratings and Climate)](https://www.kaggle.com/datasets/furkanima/worldwide-travel-cities-ratings-and-climate?resource=download)

> **Description :**
Ce jeu de données contient des informations de voyage sélectionnées pour 560 villes à travers le monde, offrant un riche mélange de données structurées et d’évaluations subjectives basées sur l’expérience. Il est conçu pour prendre en charge des applications telles que les systèmes de recommandation de voyages, l’analyse climatique, la recherche en tourisme et la planification de voyages.
> 

**Caractéristiques principales :**
Métadonnées des villes : Nom, pays, région et coordonnées.
Descriptions courtes : Résumés en une phrase de l’ambiance ou de l’attrait de chaque ville.
Informations climatiques : Températures moyennes, maximales et minimales mensuelles (au format JSON pour chaque ville).
Durées idéales : Durées de séjour suggérées comme « Week-end », « Court séjour », « Long séjour ».
Niveau de budget : Classé comme « Économique », « Intermédiaire » ou « Luxe ».
Évaluations thématiques (échelle de 0 à 5) : Culture, Aventure, Nature, Plages, Vie nocturne, Cuisine, Bien-être, Urbain.

## API

[API | World Bank Data360](https://data360.worldbank.org/en/api)

## Web Scrapping

[Indice de qualité de vie par pays 2024 Milieu de l'année](https://fr.numbeo.com/qualit%C3%A9-de-vie/classements-par-pays?title=2024-mid)

[ISO-3166 présentée par Sirius](https://www.sirius-upvm.net/doc/usuels/iso3166.html)