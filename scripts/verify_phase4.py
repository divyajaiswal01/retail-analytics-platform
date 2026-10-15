"""Verify the gold layer against the numbers found in the Phase 3 EDA.

Run from the project root:  python -m scripts.verify_phase4
Close Jupyter / any DuckDB session first (DuckDB allows one writer or reader lock at a time).
Exit code 0 = all checks match, 1 = at least one mismatch.
"""

from __future__ import annotations

import sys

import duckdb

from ingestion.config import get_warehouse_path

# (label, SQL returning one number, expected value from the EDA)
CHECKS: list[tuple[str, str, int]] = [
    ("fact_orders rows", "SELECT COUNT(*) FROM marts.fact_orders", 99_441),
    ("fact_order_items rows", "SELECT COUNT(*) FROM marts.fact_order_items", 112_650),
    ("dim_customer rows (unique people)", "SELECT COUNT(*) FROM marts.dim_customer", 96_096),
    ("delivered orders", "SELECT COUNT(*) FROM marts.fact_orders WHERE is_delivered", 96_478),
    ("late orders", "SELECT COUNT(*) FROM marts.fact_orders WHERE is_late", 7_826),
    (
        "orders with a review",
        "SELECT COUNT(*) FROM marts.fact_orders WHERE review_score IS NOT NULL",
        98_673,
    ),
    ("dim_product rows", "SELECT COUNT(*) FROM marts.dim_product", 32_951),
    ("dim_seller rows", "SELECT COUNT(*) FROM marts.dim_seller", 3_095),
]

# Informational numbers for Phase 5 (no expected value)
INFO: list[tuple[str, str]] = [
    (
        "orders in analysis window",
        "SELECT COUNT(*) FROM marts.fact_orders WHERE in_analysis_window",
    ),
    (
        "delivered orders in window",
        "SELECT COUNT(*) FROM marts.fact_orders WHERE in_analysis_window AND is_delivered",
    ),
    (
        "delivered revenue in window (BRL)",
        "SELECT ROUND(SUM(delivered_revenue), 2) FROM marts.fact_orders WHERE in_analysis_window",
    ),
    (
        "on-time % in window",
        "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE is_late = FALSE) / "
        "NULLIF(COUNT(*) FILTER (WHERE is_late IS NOT NULL), 0), 2) "
        "FROM marts.fact_orders WHERE in_analysis_window",
    ),
    (
        "average review score in window",
        "SELECT ROUND(AVG(review_score), 3) FROM marts.fact_orders WHERE in_analysis_window",
    ),
    (
        "repeat customers (2+ orders, in window)",
        "SELECT COUNT(*) FROM (SELECT customer_key FROM marts.fact_orders "
        "WHERE in_analysis_window GROUP BY 1 HAVING COUNT(*) >= 2)",
    ),
    (
        "customers with an order in window",
        "SELECT COUNT(DISTINCT customer_key) FROM marts.fact_orders WHERE in_analysis_window",
    ),
]


def main() -> int:
    db_path = get_warehouse_path()
    if not db_path.exists():
        print(f"Warehouse not found: {db_path}. Run ingestion and dbt build first.")
        return 1

    con = duckdb.connect(str(db_path), read_only=True)
    failures = 0

    print(f"Warehouse: {db_path}\n")
    print(f"{'CHECK':<38}{'EXPECTED':>12}{'ACTUAL':>12}  STATUS")
    print("-" * 70)
    for label, sql, expected in CHECKS:
        row = con.execute(sql).fetchone()
        actual = int(row[0]) if row and row[0] is not None else 0
        ok = actual == expected
        failures += 0 if ok else 1
        print(f"{label:<38}{expected:>12,}{actual:>12,}  {'OK' if ok else 'MISMATCH'}")

    print("\nInformational (send these to Claude for Phase 5):")
    print("-" * 70)
    for label, sql in INFO:
        row = con.execute(sql).fetchone()
        print(f"{label:<42}{row[0] if row else None}")

    con.close()
    print("\nRESULT:", "ALL CHECKS MATCH" if failures == 0 else f"{failures} MISMATCH(ES)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
