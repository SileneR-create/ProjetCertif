# Projet de certification - Recommandation de destination (ML)

## 📌 Présentation
Mon projet est une application basée sur le machine learning qui analyse le profil des voyageurs pour recommander des destinations adaptées. Elle prend en compte les préférences, le budget et le style de voyage. Elle permet aussi d’identifier des destinations sous-cotées, moins connues mais intéressantes.
---

## 🧭 Architecture des données

### 🔹 MCD
👉 [Voir le MCD](mcd_merise_travel_recommender_v2.html)

### 🔹 MPD

#### 🗄️ Base de données : `BDD_Projet_Certif`

**Tables principales :**

- **Users**
  - id_user (PK)
  - nom_user

- **Destination**
  - id_destination (PK)
  - pays, ville, continent
  - climat, latitude, longitude

- **Activites**
  - id_activite (PK)
  - nom, catégorie

- **Profils_voyageurs**
  - budget
  - niveau_confort
  - durée_voyage
  - climat_souhaité

- **Recommandations**
  - score_matching
  - score_budget
  - score_activité
  - score_climat

---

## 📊 Sources de données

### 📁 Kaggle

- [Travel Destinations](https://www.kaggle.com/datasets/leondesilva1/travel-destinations)  
⚠️ Dataset non utilisé (peu pertinent)

- [Worldwide Travel Cities](https://www.kaggle.com/datasets/furkanima/worldwide-travel-cities-ratings-and-climate)  
✔️ Dataset principal :
- 560 villes
- Climat
- Budget
- Scores (culture, nature, etc.)

---

### 🌐 API

- [World Bank Data API](https://data360.worldbank.org/en/api)

---

### 🕸️ Web Scraping

- [Qualité de vie - Numbeo](https://fr.numbeo.com/qualit%C3%A9-de-vie/classements-par-pays?title=2024-mid)
- [Codes ISO 3166](https://www.sirius-upvm.net/doc/usuels/iso3166.html)