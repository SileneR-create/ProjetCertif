FROM python:3.13

WORKDIR /app

# Copier le fichier des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pour le backend, on a besoin de TOUT le code (racine + dossiers)
COPY . .

EXPOSE 8000

# Commande pour démarrer FastAPI
CMD ["uvicorn", "backend.app_api:app", "--host", "0.0.0.0", "--port", "8000"]