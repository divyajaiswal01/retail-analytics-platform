"""Cross-check the dbt marts against the raw tables using independent SQL.

Run from the project root AFTER `dbt build`:
    python -m scripts.verify_marts

Each check computes the expected value straight from the raw (text) tables and compares it
with the matching number in the marts. Exit code is 0 only if every check passes.
"""

from __future__ import annotations

import sys

import duckdb

from ingestion.config import get_warehouse_path

# (label, SQL on raw tables = expected, SQL on marts = actual)
CHECKS: list[tuple[str, str, str]] = [
    (
        "orders",
        "SELECT COUNT(*) FROM raw.orders",
        "SELECT COUNT(*) FROM marts.fact_orders",
    ),
    (
        "order items",
        "SELECT COUNT(*) FROM raw.order_items",
        "SELECT COUNT(*) FROM marts.fact_order_items",
    ),
    (
        "real customers (customer_unique_id)",
        "SELECT COUNT(DISTINCT customer_unique_id) FROM raw.customers",
        "SELECT COUNT(*) FROM marts.dim_customer",
    ),
    (
        "delivered orders",
        "SELECT COUNT(*) FROM raw.orders WHERE order_status = 'delivered'",
        "SELECT COUNT(*) FROM marts.fact_orders WHERE is_delivered",
    ),
    (
        "late orders",
        """
        SELECT COUNT(*) FROM raw.orders
        WHERE order_status = 'delivered'
          AND TRY_CAST(order_delivered_customer_date AS TIMESTAMP)
              > TRY_CAST(order_estimated_delivery_date AS TIMESTAMP)
        """,
        "SELECT COUNT(*) FROM marts.fact_orders WHERE is_late",
    ),
    (
        "orders with a review",
        "SELECT COUNT(DISTINCT order_id) FROM raw.order_reviews",
        "SELECT COUNT(*) FROM marts.fact_orders WHERE review_score IS NOT NULL",
    ),
    (
        "delivered revenue (BRL)",
        """
        SELECT ROUND(SUM(TRY_CAST(i.price AS DOUBLE)), 2)
        FROM raw.order_items i
        JOIN raw.orders o USING (order_id)
        WHERE o.order_status = 'delivered'
        """,
        "SELECT ROUND(SUM(delivered_revenue), 2) FROM marts.fact_orders",
    ),
    (
        "total payments (BRL)",
        "SELECT ROUND(SUM(TRY_CAST(payment_value AS DOUBLE)), 2) FROM raw.order_payments",
        "SELECT ROUND(SUM(payment_total), 2) FROM marts.fact_orders",
    ),
]


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    """Return the single numeric value produced by a query."""
    row = con.execute(sql).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def main() -> int:
    db_path = get_warehouse_path()
    if not db_path.exists():
        print(f"Warehouse not found: {db_path}. Run ingestion and dbt build first.")
        return 1

    con = duckdb.connect(str(db_path), read_only=True)
    failures = 0
    print(f"Warehouse: {db_path}\n")
    print(f"{'check':<38}{'raw (expected)':>18}{'marts (actual)':>18}  result")
    print("-" * 82)
    try:
        for label, expected_sql, actual_sql in CHECKS:
            expected = scalar(con, expected_sql)
            actual = scalar(con, actual_sql)
            ok = abs(expected - actual) < 0.01
            failures += 0 if ok else 1
            print(f"{label:<38}{expected:>18,.2f}{actual:>18,.2f}  {'PASS' if ok else 'FAIL'}")
    finally:
        con.close()

    print("-" * 82)
    print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
