from langchain_core.tools import tool
from pydantic import BaseModel, Field
import pandas as pd
from sqlalchemy import text
from db.connection import get_engine

class RevenueTrendInput(BaseModel):
    n_periods: int = Field(12, description="Nombre de mois à analyser (max 24)")

@tool(args_schema=RevenueTrendInput)
def get_revenue_trend(n_periods: int = 12) -> dict:
    """
    Tendance de revenus mensuelle avec croissance.
    Retourne: {period, revenue, orders_count, growth_pct}.
    Utiliser pour: évolution CA, tendances, saisonnalité.
    """
    sql = text("""
        WITH monthly AS (
            SELECT
                TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') AS period,
                SUM(p.payment_value)                            AS revenue,
                COUNT(DISTINCT o.order_id)                      AS orders_count
            FROM orders o
            JOIN payments p ON p.order_id = o.order_id
            WHERE o.order_status = 'delivered'
              AND o.order_purchase_timestamp IS NOT NULL
            GROUP BY 1 ORDER BY 1 DESC LIMIT :n
        )
        SELECT period, ROUND(revenue::NUMERIC, 2) AS revenue, orders_count,
            ROUND(
                (revenue - LAG(revenue) OVER (ORDER BY period))
                / NULLIF(LAG(revenue) OVER (ORDER BY period), 0) * 100
            , 1) AS growth_pct
        FROM monthly ORDER BY period ASC
    """)
    df = pd.read_sql(sql, get_engine(), params={"n": min(n_periods, 24)})
    return {
        "data": df.to_dict("records"),
        "total_revenue": float(df["revenue"].sum()),
        "avg_monthly": float(df["revenue"].mean().round(2)),
    }

class TopProductsInput(BaseModel):
    n: int = Field(10, description="Nombre de catégories (max 50)")
    metric: str = Field("revenue", description="'revenue' ou 'volume'")

@tool(args_schema=TopProductsInput)
def get_top_products(n: int = 10, metric: str = "revenue") -> dict:
    """
    Top N catégories par CA ou volume de commandes.
    Utiliser pour: produits stars, performances par catégorie.
    """
    order_col = "revenue DESC" if metric == "revenue" else "volume DESC"
    sql = text(f"""
        SELECT
            COALESCE(pr.product_category_name_english, 'unknown') AS category,
            ROUND(SUM(p.payment_value)::NUMERIC, 2) AS revenue,
            COUNT(DISTINCT o.order_id)               AS volume,
            ROUND(AVG(r.review_score)::NUMERIC, 1)   AS avg_score
        FROM orders o
        JOIN order_items oi ON oi.order_id   = o.order_id
        JOIN products    pr ON pr.product_id = oi.product_id
        JOIN payments    p  ON p.order_id    = o.order_id
        LEFT JOIN reviews r ON r.order_id    = o.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY {order_col} LIMIT :n
    """)
    df = pd.read_sql(sql, get_engine(), params={"n": min(n, 50)})
    return {"data": df.to_dict("records")}

@tool
def get_aov_analysis() -> dict:
    """
    Panier moyen (AOV) global et top 10 états brésiliens.
    Utiliser pour: valeur commandes, comparaisons régionales.
    """
    engine = get_engine()
    global_row = pd.read_sql(text("""
        WITH totals AS (
            SELECT SUM(p.payment_value) AS total
            FROM orders o JOIN payments p ON p.order_id = o.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY o.order_id
        )
        SELECT ROUND(AVG(total)::NUMERIC,2) AS aov,
               ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total)::NUMERIC,2) AS median
        FROM totals
    """), engine).iloc[0]

    by_state = pd.read_sql(text("""
        SELECT c.customer_state AS state,
               ROUND(AVG(sub.total)::NUMERIC,2) AS aov
        FROM (
            SELECT o.customer_id, SUM(p.payment_value) AS total
            FROM orders o JOIN payments p ON p.order_id=o.order_id
            WHERE o.order_status='delivered' GROUP BY o.order_id, o.customer_id
        ) sub
        JOIN customers c ON c.customer_id = sub.customer_id
        GROUP BY 1 ORDER BY aov DESC LIMIT 10
    """), engine)

    return {
        "global_aov": float(global_row["aov"]),
        "median_aov": float(global_row["median"]),
        "top_states": by_state.to_dict("records"),
    }

@tool(args_schema=TopProductsInput)
def get_top_products_trend(n: int = 10) -> dict:
    """
    Tendance mensuelle des revenus pour les Top N catégories de produits.
    Utiliser pour: "courbe évolutive des produits", "évolution par catégorie".
    """
    engine = get_engine()
    # 1. Identifier les top N catégories
    top_cats = pd.read_sql(text("""
        SELECT pr.product_category_name_english AS cat
        FROM order_items oi
        JOIN products pr ON pr.product_id = oi.product_id
        JOIN payments p ON p.order_id = oi.order_id
        WHERE pr.product_category_name_english IS NOT NULL
        GROUP BY 1 ORDER BY SUM(p.payment_value) DESC LIMIT :n
    """), engine, params={"n": n})["cat"].tolist()

    if not top_cats: return {"data": []}

    # 2. Récupérer la tendance pour ces catégories
    sql = text("""
        SELECT
            TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') AS period,
            pr.product_category_name_english AS category,
            ROUND(SUM(p.payment_value)::NUMERIC, 2) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products pr ON pr.product_id = oi.product_id
        JOIN payments p ON p.order_id = o.order_id
        WHERE o.order_status = 'delivered'
          AND pr.product_category_name_english IN :cats
          AND o.order_purchase_timestamp >= '2017-01-01'
        GROUP BY 1, 2 ORDER BY 1 ASC
    """)
    df = pd.read_sql(sql, engine, params={"cats": tuple(top_cats)})
    
    # Pivot pour avoir une ligne par période et une colonne par catégorie pour un line chart multi-séries si besoin
    # Mais le ChartAgent préfère souvent du format "long" ou gère le pivot. 
    # create_line_chart actuel ne gère qu'une seule série (x_key, y_key).
    
    return {
        "data": df.to_dict("records"),
        "categories": top_cats
    }