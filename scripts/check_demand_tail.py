"""Check whether the most recent weeks of demand look incomplete or understated.

Two views:
1. Weekly: share of items delivered vs still in progress. If recent weeks show a sharply lower
   delivered share, delivered demand is understated by orders still in transit.
2. Daily: items per day over the last 21 days of the window. If days are normal and then collapse
   at the very end, the data probably stops being complete before its nominal end date.

Run from the project root:  python -m scripts.check_demand_tail [weeks]
Close Jupyter / any other DuckDB session first.
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from ingestion.config import get_warehouse_path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.1f}")

WEEKLY_QUERY = """
WITH last_week AS (SELECT MAX(week_start) AS week_start FROM marts.mart_weekly_category_demand),
weekly AS (
    SELECT d.week_start,
           COUNT(*) AS items_all_statuses,
           COUNT(*) FILTER (WHERE i.is_delivered) AS items_delivered,
           COUNT(*) FILTER (
               WHERE i.order_status IN ('created', 'approved', 'invoiced', 'processing', 'shipped')
           ) AS items_in_progress,
           COUNT(*) FILTER (WHERE i.order_status IN ('canceled', 'unavailable')) AS items_cancelled
    FROM marts.fact_order_items AS i
    INNER JOIN marts.dim_date AS d ON i.order_date = d.date_day
    WHERE i.in_analysis_window
      AND d.week_start <= (SELECT week_start FROM last_week)
    GROUP BY d.week_start
)
SELECT w.week_start,
       w.items_all_statuses,
       w.items_delivered,
       100.0 * w.items_delivered / w.items_all_statuses AS delivered_pct,
       w.items_in_progress,
       100.0 * w.items_in_progress / w.items_all_statuses AS in_progress_pct,
       w.items_cancelled
FROM weekly AS w
ORDER BY w.week_start DESC
LIMIT ?
"""

DAILY_QUERY = """
SELECT i.order_date,
       d.day_name,
       COUNT(*) AS items_all_statuses,
       COUNT(*) FILTER (WHERE i.is_delivered) AS items_delivered
FROM marts.fact_order_items AS i
INNER JOIN marts.dim_date AS d ON i.order_date = d.date_day
WHERE i.order_date BETWEEN (SELECT window_end FROM marts.metrics_summary) - 20
                       AND (SELECT window_end FROM marts.metrics_summary)
GROUP BY i.order_date, d.day_name
ORDER BY i.order_date
"""


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    n_weeks = int(args[0]) if args else 12
    db_path = get_warehouse_path()
    if not db_path.exists():
        print(f"Warehouse not found: {db_path}. Run ingestion and dbt build first.")
        return 1
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        weekly = con.execute(WEEKLY_QUERY, [n_weeks]).df().sort_values("week_start")
        daily = con.execute(DAILY_QUERY).df()
    except duckdb.CatalogException as exc:
        print(f"Required table not found ({exc}). Run `dbt build` first.")
        return 1
    finally:
        con.close()
    print(f"=== LAST {n_weeks} COMPLETE WEEKS: ALL ITEMS BY ORDER STATUS (all categories) ===")
    print(weekly.to_string(index=False))
    print("\n=== LAST 21 DAYS OF THE ANALYSIS WINDOW: ITEMS PER DAY (all categories) ===")
    print(daily.to_string(index=False))
    print(
        "\nHow to read the weekly table: a sharply lower delivered_pct and higher"
        "\nin_progress_pct in the newest weeks means delivered demand is understated"
        "\nby orders still in transit."
        "\nHow to read the daily table: normal days followed by a collapse in the final"
        "\ndays suggests the data stops being complete before its end date; steadily"
        "\nlow days suggest real demand."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
