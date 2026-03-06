from langchain_core.tools import tool
import pandas as pd
from sqlalchemy import text
from db.connection import get_engine

@tool
def get_cohort_retention() -> dict:
    """
    Matrice de rétention par cohorte mensuelle (12 derniers mois, M+0 à M+5).
    Cohorte = clients ayant fait leur 1er achat le même mois.
    Utiliser pour: fidélisation, rétention client, LTV.
    """
    sql = text("""
        WITH customer_orders AS (
            SELECT c.customer_unique_id,
                   DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS order_month
            FROM orders o JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered'
              AND o.order_purchase_timestamp IS NOT NULL
        ),
        cohorts AS (
            SELECT customer_unique_id, order_month,
                   MIN(order_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
            FROM customer_orders
        ),
        periods AS (
            SELECT cohort_month,
                   EXTRACT(YEAR FROM AGE(order_month, cohort_month)) * 12
                   + EXTRACT(MONTH FROM AGE(order_month, cohort_month)) AS period,
                   COUNT(DISTINCT customer_unique_id) AS customers
            FROM cohorts GROUP BY 1, 2
        ),
        sizes AS (
            SELECT cohort_month, customers AS size
            FROM periods WHERE period = 0
        )
        SELECT TO_CHAR(p.cohort_month,'YYYY-MM') AS cohort,
               p.period::INT AS period,
               ROUND(p.customers::NUMERIC / s.size * 100, 1) AS retention_pct
        FROM periods p JOIN sizes s ON s.cohort_month = p.cohort_month
        WHERE p.cohort_month >= (SELECT MAX(cohort_month) - INTERVAL '12 months' FROM sizes)
          AND p.period <= 5
        ORDER BY 1, 2
    """)
    df = pd.read_sql(sql, get_engine())
    matrix = df.pivot(index="cohort", columns="period", values="retention_pct").fillna(0)
    matrix.columns = [f"M+{int(c)}" for c in matrix.columns]
    avg = {col: round(float(matrix[col].mean()), 1) for col in matrix.columns if col != "M+0"}
    return {"matrix": matrix.to_dict(), "avg_by_period": avg, "m1_avg": avg.get("M+1", 0)}

@tool
def get_rfm_segments() -> dict:
    """
    Segmentation RFM : Champions, Loyal, Promising, At Risk, Lost.
    Utiliser pour: identifier les meilleurs clients, actions marketing ciblées.
    """
    sql = text("""
        WITH raw AS (
            SELECT c.customer_unique_id,
                   DATE_PART('day', NOW() - MAX(o.order_purchase_timestamp)) AS recency,
                   COUNT(DISTINCT o.order_id)  AS frequency,
                   SUM(p.payment_value)         AS monetary
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN payments  p ON p.order_id    = o.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY c.customer_unique_id
        ),
        scored AS (
            SELECT *,
                NTILE(4) OVER (ORDER BY recency DESC)   AS r_score,
                NTILE(4) OVER (ORDER BY frequency ASC)  AS f_score,
                NTILE(4) OVER (ORDER BY monetary ASC)   AS m_score
            FROM raw
        ),
        segmented AS (
            SELECT *, CASE
                WHEN r_score >= 4 AND f_score >= 3 THEN 'Champions'
                WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal'
                WHEN r_score >= 3                  THEN 'Promising'
                WHEN r_score <= 2 AND f_score >= 2 THEN 'At Risk'
                ELSE 'Lost'
            END AS segment
            FROM scored
        )
        SELECT segment,
               COUNT(*) AS count,
               ROUND(AVG(monetary)::NUMERIC,2)  AS avg_revenue,
               ROUND(SUM(monetary)::NUMERIC,2)  AS total_revenue,
               ROUND(COUNT(*)*100.0 / SUM(COUNT(*)) OVER (),1) AS pct
        FROM segmented
        GROUP BY 1 ORDER BY total_revenue DESC
    """)
    df = pd.read_sql(sql, get_engine())
    return {"segments": df.to_dict("records"), "total_customers": int(df["count"].sum())}

@tool
def get_churn_rate() -> dict:
    """
    Taux de churn : % clients n'ayant pas racheté après le 1er achat.
    """
    row = pd.read_sql(text("""
        WITH stats AS (
            SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
            FROM orders o JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered' GROUP BY 1
        )
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN orders=1 THEN 1 ELSE 0 END) AS one_time,
               ROUND(SUM(CASE WHEN orders=1 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct,
               ROUND(AVG(orders)::NUMERIC,2) AS avg_orders
        FROM stats
    """), get_engine()).iloc[0]
    return {
        "one_time_pct": float(row["pct"]),
        "repeat_pct": round(100 - float(row["pct"]), 1),
        "total_customers": int(row["total"]),
        "avg_orders": float(row["avg_orders"]),
    }