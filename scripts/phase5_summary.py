"""Print the headline Phase 5 results in one block you can copy and share.

Run from the project root:  python -m scripts.phase5_summary
Close Jupyter / any other DuckDB session first.
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from ingestion.config import get_warehouse_path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")


def section(con: duckdb.DuckDBPyConnection, title: str, sql: str) -> None:
    """Print one titled result table."""
    print(f"\n=== {title} ===")
    print(con.execute(sql).df().to_string(index=False))


def main() -> int:
    db_path = get_warehouse_path()
    if not db_path.exists():
        print(f"Warehouse not found: {db_path}. Run ingestion and dbt build first.")
        return 1
    con = duckdb.connect(str(db_path), read_only=True)

    section(con, "HEADLINE KPIs", "SELECT * FROM marts.metrics_summary")
    section(con, "MONTHLY KPIs", "SELECT * FROM marts.metrics_kpis ORDER BY year_month")
    section(
        con,
        "RFM SEGMENTS",
        """
        SELECT segment,
               COUNT(*) AS customers,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
               ROUND(SUM(monetary), 2) AS revenue,
               ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS revenue_pct,
               ROUND(AVG(monetary), 2) AS avg_spend
        FROM marts.mart_customer_rfm GROUP BY 1 ORDER BY revenue DESC
        """,
    )
    section(
        con,
        "RETENTION (weighted average by months since first order)",
        """
        SELECT months_since_first,
               COUNT(*) AS cohorts,
               SUM(cohort_size) AS customers,
               SUM(active_customers) AS active,
               ROUND(100.0 * SUM(active_customers) / SUM(cohort_size), 2) AS retention_pct
        FROM marts.mart_cohort_retention
        WHERE months_since_first <= 12
        GROUP BY 1 ORDER BY 1
        """,
    )
    section(
        con, "DELIVERY IMPACT", "SELECT * FROM marts.mart_delivery_impact ORDER BY bucket_order"
    )
    section(con, "FIRST DELIVERY VS REPEAT", "SELECT * FROM marts.mart_delivery_vs_repeat")
    section(
        con,
        "TOP 10 CATEGORIES",
        """
        SELECT revenue_rank, category, revenue, revenue_share_pct, cumulative_share_pct,
               revenue_prior_period, revenue_current_period, yoy_growth_pct
        FROM marts.mart_category_performance ORDER BY revenue_rank LIMIT 10
        """,
    )
    section(
        con,
        "TOP 10 STATES BY REVENUE",
        """
        SELECT state, customers, delivered_orders, delivered_revenue, revenue_share_pct,
               on_time_pct, avg_delivery_days, avg_review_score
        FROM marts.mart_state_performance ORDER BY delivered_revenue DESC LIMIT 10
        """,
    )
    section(
        con,
        "5 STATES WITH LOWEST ON-TIME % (min 500 orders)",
        """
        SELECT state, delivered_orders, on_time_pct, avg_delivery_days, avg_review_score
        FROM marts.mart_state_performance
        WHERE delivered_orders >= 500 ORDER BY on_time_pct LIMIT 5
        """,
    )
    section(
        con,
        "SELLERS (rankable) - 10 LOWEST REVIEW SCORES",
        """
        SELECT seller_key, state, orders, revenue, late_pct, avg_review_score,
               overall_late_pct, overall_avg_review_score
        FROM marts.mart_seller_performance
        WHERE meets_min_volume ORDER BY avg_review_score LIMIT 10
        """,
    )
    section(
        con,
        "SELLER COVERAGE",
        """
        SELECT COUNT(*) AS sellers,
               COUNT(*) FILTER (WHERE meets_min_volume) AS rankable_sellers,
               ROUND(100.0 * SUM(revenue) FILTER (WHERE meets_min_volume) / SUM(revenue), 2)
                   AS revenue_pct_from_rankable
        FROM marts.mart_seller_performance
        """,
    )
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
