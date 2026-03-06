from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import app as fastapi_app
from data_loader import init_data, shutdown_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initialisation DataMind (Lifespan start)...")
    try:
        # On tente de charger les stats de base, mais on ne bloque pas si ça échoue
        init_data()
        print("✓ DataMind prêt.")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'initialisation (non-bloquant) : {e}")
    yield
    print("Arrêt DataMind (Lifespan end)...")
    shutdown_data()

# On attache le lifespan
fastapi_app.router.lifespan_context = lifespan

# CRITIQUE : Uvicorn cherche l'objet 'app' dans le module désigné (main:app)
app = fastapi_app

# Petit log pour confirmer le chargement du module
print("✓ Module main.py chargé avec succès (app object exposed).")