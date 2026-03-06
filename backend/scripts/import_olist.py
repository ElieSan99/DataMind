import os, sys
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("../.env")

DATA_DIR = Path("./data/raw")
DATABASE_URL = os.getenv('DATABASE_URL')
#print(DATABASE_URL)
if not DATABASE_URL:
    print("DATABASE_URL manquant dans .env"); sys.exit(1)

engine = create_engine(DATABASE_URL, echo=False)

def load(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Introuvable : {path}")
    df = pd.read_csv(path)
    print(f"  ← {filename} : {len(df):,} lignes")
    return df

def insert(df: pd.DataFrame, table: str, cols: list[str]):
    df[cols].drop_duplicates().to_sql(
        table, engine, if_exists="append",
        index=False, chunksize=100
    )
    print(f"  ✓ {table} : {len(df[cols].drop_duplicates()):,} lignes")

def run():
    print("Connexion Supabase...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ OK\n Nettoyage tables existantes...")
    with engine.begin() as conn:
        for t in ["reviews","payments","order_items","orders","customers","products"]:
            conn.execute(text(f"TRUNCATE {t} CASCADE"))
    print("✓ Tables vidées\n Chargement CSV...")

    cust  = load("olist_customers_dataset.csv")
    prod  = load("olist_products_dataset.csv")
    cats  = load("product_category_name_translation.csv")
    ords  = load("olist_orders_dataset.csv")
    items = load("olist_order_items_dataset.csv")
    pays  = load("olist_order_payments_dataset.csv")
    revs  = load("olist_order_reviews_dataset.csv")

    # Nettoie les dates orders
    for col in ["order_purchase_timestamp","order_approved_at","order_delivered_customer_date"]:
        ords[col] = pd.to_datetime(ords[col], errors="coerce")

    # Ajoute la traduction de catégorie en anglais dans products
    prod = prod.merge(cats, on="product_category_name", how="left")

    # IDs valides pour respecter les FK
    valid_cust = set(cust["customer_id"])
    valid_prod = set(prod["product_id"])
    ords_clean = ords[ords["customer_id"].isin(valid_cust)]
    valid_ord  = set(ords_clean["order_id"])

    print("\nInsertion PostgreSQL...")
    insert(cust, "customers", ["customer_id","customer_unique_id","customer_zip_code_prefix","customer_city","customer_state"])
    insert(prod, "products",   ["product_id","product_category_name","product_category_name_english"])
    insert(ords_clean, "orders", ["order_id","customer_id","order_status","order_purchase_timestamp","order_approved_at","order_delivered_customer_date"])

    items_c = items[items["order_id"].isin(valid_ord) & items["product_id"].isin(valid_prod)]
    insert(items_c, "order_items", ["order_id","order_item_id","product_id","price","freight_value"])

    pays_c = pays[pays["order_id"].isin(valid_ord)]
    insert(pays_c, "payments", ["order_id","payment_sequential","payment_type","payment_installments","payment_value"])

    revs_c = revs[revs["order_id"].isin(valid_ord)].drop_duplicates(subset=["review_id","order_id"])
    insert(revs_c, "reviews", ["review_id","order_id","review_score","review_creation_date"])

    print("\nVérification :")
    with engine.connect() as conn:
        for t in ["customers","products","orders","order_items","payments","reviews"]:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:20s}: {n:,}")
    print("\nImport terminé. Tu peux supprimer backend/data/ si tu veux.")

if __name__ == "__main__": run()