CREATE TABLE IF NOT EXISTS Users (
    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_user TEXT
    );
            
CREATE TABLE IF NOT EXISTS Profils_voyageurs(
    id_profil INTEGER PRIMARY KEY AUTOINCREMENT,
    id_user INTEGER FOREING KEY,
    budget INTEGER
    niveau_confort INTEGER
    durée_voyage_jour INTEGER,
    nb_voyageur INTEGER,
    climat_souhaite TEXT
    );

CREATE TABLE IF NOT EXISTS Activites(
    id_activite INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_activite TEXT, 
    categorie TEXT
    );

CREATE TABLE IF NOT EXISTS Destinations(
    id_destination INTEGER PRIMARY KEY AUTOINCREMENT,
    pays TEXT,
    ville TEXT,
    code_pays_iso3 TEXT,
    continent TEXT,
    type_climat TEXT?
    latitude FLOAT,
    longitude FLOAT
    );

CREATE TABLE IF NOT EXISTS preference_activite(
    id_user INTEGER FOREIGN KEY,
    id_activite INTEGER FOREIGN KEY,
    priorite
    );

CREATE TABLE IF NOT EXISTS Recommandations(
    id_recommandation INTEGER PRIMARY KEY AUTOINCREMENT,
    id_user INTEGER FOREIGN KEY,
    id_destination INTEGER FOREIGN KEY,
    score_matching INTEGER,
    score_budget INTEGER,
    score_activité INTEGER,
    score_securite INTEGER,
    score_climat INTEGER,
    date_generation DATE
    );

CREATE TABLE IF NOT EXISTS activites_destination(
    id_destination INTEGER FOREIGN KEY,
    id_activite INTEGER FOREIGN KEY
    );

CREATE TABLE IF NOT EXISTS saisonnalites(
    id_saisonnalite INTEGER PRIMARY KEY AUTOINCREMENT,
    id_destination INTEGER FOREIGN KEY,
    mois INTEGER,
    condition_meteo TEXT,
    temps_moy_celsius INTEGER,
    precipitation_mm INTEGER?
    recommandation TEXT
    );

CREATE TABLE IF NOT EXISTS Indicateurs_WorldBank(
    id_worldbank INTEGER PRIMARY KEY,
    id_destination INTEGER FOREIGN KEY,
    code_indicateur TEXT,
    libele TEXT,
    categorie TEXT,
    valeur INTEGER,
    annee INTEGER,
    date_import DATE
    );
            '''