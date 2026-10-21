"""Print the headline Phase 6 forecasting results in one block you can copy and share.

Run from the project root:  python -m scripts.phase6_summary
Close Jupyter / any other DuckDB session first.
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from ingestion.config import get_warehouse_path

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")


def section(con: duckdb.DuckDBPyConnection, title: str, sql: str) -> None:
    """Print one titled result table."""
    print(f"\n=== {title} ===")
    print(con.execute(sql).df().to_string(index=False))


def main() -> int:
    db_path = get_warehouse_path()
    if not db_path.exists():
        print(f"Warehouse not found: {db_path}. Run ingestion, dbt build and forecasting first.")
        return 1
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        section(
            con,
            "RUN",
            """
            SELECT run_at_utc, categories, weeks, first_week, last_week, origins,
                   selection_origins, holdout_origins, holdout_interval_coverage_pct
            FROM forecast.run_log
            """,
        )
        section(
            con,
            "ACCURACY BY SCOPE (lower WAPE is better; holdout_origins is the honest test)",
            """
            SELECT scope, model, rows, ROUND(coverage_pct, 1) AS coverage_pct, wape, bias, mae,
                   median_category_wape
            FROM forecast.accuracy_summary
            ORDER BY CASE scope WHEN 'holdout_origins' THEN 1 WHEN 'all_origins' THEN 2
                                WHEN 'full_year_origins' THEN 3 ELSE 4 END, wape
            """,
        )
        section(
            con,
            "HOLDOUT ERROR BY HORIZON (WAPE, weeks ahead)",
            """
            SELECT horizon,
                   ROUND(MAX(CASE WHEN model = 'naive' THEN wape END), 3) AS naive,
                   ROUND(MAX(CASE WHEN model = 'moving_average_4' THEN wape END), 3)
                       AS moving_avg_4,
                   ROUND(MAX(CASE WHEN model = 'ets' THEN wape END), 3) AS ets,
                   ROUND(MAX(CASE WHEN model = 'lightgbm' THEN wape END), 3) AS lightgbm,
                   ROUND(MAX(CASE WHEN model = 'selected' THEN wape END), 3) AS selected
            FROM forecast.horizon_accuracy GROUP BY horizon ORDER BY horizon
            """,
        )
        section(
            con,
            "MODEL SELECTION (chosen on the earliest origins)",
            """
            SELECT category, chosen_model, best_baseline, best_baseline_wape,
                   best_candidate, best_candidate_wape, improvement_pct
            FROM forecast.model_selection
            """,
        )
        section(
            con,
            "CATEGORY UNCERTAINTY AND NEXT-PERIOD OUTLOOK (ranked, most uncertain first)",
            """
            SELECT uncertainty_rank, category, chosen_model, holdout_wape, holdout_bias,
                   median_relative_interval_width AS interval_width, forecast_units,
                   actual_units_last_period, change_vs_last_period_pct
            FROM forecast.category_uncertainty ORDER BY uncertainty_rank
            """,
        )
        section(
            con,
            "FORECAST TOTALS BY WEEK (all forecast categories)",
            """
            SELECT week_start, horizon, ROUND(SUM(forecast_units), 1) AS forecast_units,
                   ROUND(SUM(lower_units), 1) AS lower_units,
                   ROUND(SUM(upper_units), 1) AS upper_units
            FROM forecast.weekly_forecast GROUP BY 1, 2 ORDER BY 1
            """,
        )
        section(
            con,
            "RECENT ACTUAL WEEKLY UNITS (same categories, last 10 weeks, for context)",
            """
            SELECT week_start, SUM(units) AS units
            FROM marts.mart_weekly_category_demand
            WHERE category_revenue_rank <= (SELECT categories FROM forecast.run_log)
            GROUP BY 1 ORDER BY 1 DESC LIMIT 10
            """,
        )
    except duckdb.CatalogException as exc:
        print(f"Forecast tables not found ({exc}). Run `python -m forecasting.train` first.")
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
