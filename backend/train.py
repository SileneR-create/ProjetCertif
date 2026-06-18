import os
import pandas as pd
import numpy as np
import mlflow
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, silhouette_score, classification_report

# Configuration de l'URI réseau MLflow pour Docker
if "MLFLOW_TRACKING_URI" not in os.environ:
    mlflow.set_tracking_uri("http://mlflow:5000")

try:
    mlflow.set_experiment("TravelMatch_Model_Exploration")
except Exception as e:
    print(f"❌ Impossible de lier l'expérience MLflow : {e}")

ACTIVITY_FEATURES = ["nature", "patrimoine", "culture", "restaurant", "nightlife", "loisirs"]

def run_model_training(data_path="data/dataset.csv", n_clusters=6, n_estimators=100):
    """Entraîne une version spécifique de l'IA et loggue les métriques numériques globales pour comparaison."""
    
    # Lecture des données globales historiques
    if not os.path.exists(data_path):
        print(f"❌ Fichier de données introuvable à l'adresse : {data_path}")
        return
        
    df = pd.read_csv(data_path)
    
    # Préparation / Groupement des données comme dans le moteur original
    city_group = df.groupby("city")[ACTIVITY_FEATURES].mean().reset_index()
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(city_group[ACTIVITY_FEATURES])
    
    # Nom du Run basé sur ses hyperparamètres de structure
    run_name = f"RF_Trees_{n_estimators}_KM_Clusters_{n_clusters}"
    
    with mlflow.start_run(run_name=run_name):
        # 1. Enregistrement des hyperparamètres (Colonnes de comparaison)
        mlflow.log_param("n_clusters", int(n_clusters))
        mlflow.log_param("n_estimators", int(n_estimators))
        
        # 2. Pipeline d'apprentissage : Clustering K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        city_group["cluster_id"] = kmeans.fit_predict(X_scaled)
        
        # 3. Pipeline d'apprentissage : Classifieur Random Forest
        rf = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        rf.fit(city_group[ACTIVITY_FEATURES], city_group["cluster_id"])
        
        # 4. Évaluation des performances théoriques
        y_true = city_group["cluster_id"]
        y_pred = rf.predict(city_group[ACTIVITY_FEATURES])
        
        # Calcul des scores numériques simples (pour colonnes MLflow UI)
        acc = accuracy_score(y_true, y_pred)
        sil = silhouette_score(X_scaled, city_group["cluster_id"])
        
        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        f1_macro = report["macro avg"]["f1-score"]
        
        # 5. Log des métriques numériques GLOBALES (Directement visibles en colonnes !)
        mlflow.log_metric("model_accuracy", float(acc))
        mlflow.log_metric("silhouette_score", float(sil))
        mlflow.log_metric("f1_score_macro", float(f1_macro))
        
        # Sauvegarde facultative du modèle physique dans MLflow
        mlflow.sklearn.log_model(rf, "random_forest_model")
        mlflow.sklearn.log_model(kmeans, "kmeans_model")
        
        print(f"🎯 Modèle enregistré sous '{run_name}' : Acc={acc:.2f} | Sil={sil:.2f} | F1={f1_macro:.2f}")

if __name__ == "__main__":
    # Script de test : Lancez 3 versions à comparer pour votre présentation au jury
    # Remplacez "data/dataset.csv" par le vrai chemin de votre fichier CSV si nécessaire
    run_model_training(data_path="backend/data.csv", n_clusters=4, n_estimators=50)
    run_model_training(data_path="backend/data.csv", n_clusters=6, n_estimators=100)
    run_model_training(data_path="backend/data.csv", n_clusters=8, n_estimators=150)