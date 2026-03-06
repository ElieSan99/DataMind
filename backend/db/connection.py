import os
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv("../.env")

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ WARNING: DATABASE_URL is missing. Database features will be unavailable.")
        return None # On ne crash pas, on laisse l'app démarrer

    _engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
        pool_pre_ping=True,   # vérifie avant usage
        pool_recycle=3600,    # renouvelle après 1h
        connect_args={"sslmode": "require"},  # obligatoire Supabase
        echo=False,
    )
    print(f"✓ SQLAlchemy engine created (pool={os.getenv('DB_POOL_SIZE', 5)})")
    return _engine

def dispose_engine():
    global _engine
    if _engine is not None:
        _engine.dispose(); _engine = None