from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import app as fastapi_app
from data_loader import init_data, shutdown_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initialisation DataMind...")
    try:
        init_data()
        print("✓ DataMind prêt.")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'initialisation : {e}")
    yield
    shutdown_data()

fastapi_app.router.lifespan_context = lifespan