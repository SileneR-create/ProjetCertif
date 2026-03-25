CREATE TABLE IF NOT EXISTS Users (
    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_user TEXT
);
            
CREATE TABLE IF NOT EXISTS Profils_voyageurs(
    id_profil INTEGER PRIMARY KEY AUTOINCREMENT,
    budget INTEGER,
    niveau_confort INTEGER,
    durée_voyage_jour INTEGER,
    nb_voyageur INTEGER,
    climat_souhaite TEXT,
    id_user INTEGER,
    FOREIGN KEY(id_user)
    REFERENCES Users(id_user)
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
    type_climat TEXT,
    latitude FLOAT,
    longitude FLOAT
);

CREATE TABLE IF NOT EXISTS preference_activite(
    priorite TEXT,
    id_user INTEGER,
    id_activite INTEGER,
    FOREIGN KEY(id_user)
    REFERENCES Users(id_user),
    FOREIGN KEY(id_activite)
    REFERENCES Activites(id_activite)
);

CREATE TABLE IF NOT EXISTS Recommandations(
    id_recommandation INTEGER PRIMARY KEY AUTOINCREMENT,
    score_matching INTEGER,
    score_budget INTEGER,
    score_activité INTEGER,
    score_securite INTEGER,
    score_climat INTEGER,
    date_generation DATE,
    id_user INTEGER,
    id_destination INTEGER, 
    FOREIGN KEY(id_user)
    REFERENCES Users(id_user),
    FOREIGN KEY(id_destination)
    REFERENCES Destinations(id_destination)
);

CREATE TABLE IF NOT EXISTS activites_destination(
    id_destination INTEGER,
    id_activite INTEGER,
    FOREIGN KEY(id_destination)
    REFERENCES Destinations(id_destination),
    FOREIGN KEY(id_activite)
    REFERENCES Activites(id_activite)
);

CREATE TABLE IF NOT EXISTS saisonnalites(
    id_saisonnalite INTEGER PRIMARY KEY AUTOINCREMENT,
    mois INTEGER,
    condition_meteo TEXT,
    temps_moy_celsius INTEGER,
    precipitation_mm INTEGER,
    recommandation TEXT,
    id_destination INTEGER,
    FOREIGN KEY (id_destination)
    REFERENCES Destinations(id_destination)

);

CREATE TABLE IF NOT EXISTS Indicateurs_WorldBank(
    id_worldbank INTEGER PRIMARY KEY,
    code_indicateur TEXT,
    libele TEXT,
    categorie TEXT,
    valeur INTEGER,
    annee INTEGER,
    date_import DATE,
    id_destination INTEGER,
    FOREIGN KEY(id_destination) 
    REFERENCES Destinations(id_destination)
);