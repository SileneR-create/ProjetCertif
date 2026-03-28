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
    temperature_souhaite TEXT,
    id_user INTEGER,
    FOREIGN KEY(id_user)
    REFERENCES Users(id_user)
);

CREATE TABLE IF NOT EXISTS Activites(
    id_activite INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_activite TEXT
);

CREATE TABLE IF NOT EXISTS Destinations(
    id_destination INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT,
    City TEXT,
    code_3L TEXT,
    region TEXT,
    short_description TEXT,
    latitude FLOAT,
    longitude FLOAT
);

CREATE TABLE IF NOT EXISTS preference_activite(
    priorite TEXT,
    id_profil INTEGER,
    id_activite INTEGER,
    FOREIGN KEY(id_profil)
    REFERENCES Profils_voyageurs(id_profil),
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
    id_profil INTEGER,
    id_destination INTEGER, 
    FOREIGN KEY(id_profil)
    REFERENCES Profils_voyageurs(id_profil),
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

CREATE TABLE IF NOT EXISTS meteo(
    id_meteo INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT,
    code_3L TEXT,
    City TEXT,
    month INTEGER,
    temp_avg FLOAT,
    temp_min FLOAT,
    temp_max FLOAT,
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
    code_3L TEXT,
    FOREIGN KEY(code_3L) 
    REFERENCES Destinations(code_3L)
);