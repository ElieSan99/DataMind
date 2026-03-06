from sqlalchemy import text
from db.connection import get_engine, dispose_engine

def init_data():
    """Appelé au démarrage FastAPI — crée le pool et vérifie la base."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM orders WHERE order_status = 'delivered') AS delivered,
                (SELECT COUNT(*) FROM customers) AS customers,
                (SELECT COUNT(*) FROM products)  AS products
        """)).fetchone()
    print(f"✓ Supabase OK — {row[0]:,} cmds livrées | {row[1]:,} clients | {row[2]:,} produits")

def shutdown_data():
    """Appelé au shutdown — ferme le pool proprement."""
    dispose_engine()
    print("✓ Pool SQLAlchemy fermé.")