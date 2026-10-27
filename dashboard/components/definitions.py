"""Plain-language KPI definitions shown as tooltips. They mirror docs/kpi_definitions.md."""

from __future__ import annotations

DEFINITIONS = {
    "revenue": "Sum of item prices of delivered orders in BRL, excluding freight.",
    "orders": "Orders with status delivered.",
    "aov": "Average order value: delivered revenue divided by delivered orders that have revenue.",
    "customers": "Distinct customers (real people) with a delivered order.",
    "repeat_rate": "Customers with 2 or more delivered orders divided by customers with 1 or more.",
    "on_time": (
        "Delivered orders that arrived on or before the estimated date, divided by delivered "
        "orders with a known delivery date."
    ),
    "delivery_days": "Average days from purchase to delivery.",
    "review": "Average review score (1-5) of delivered orders; the most recent review per order.",
    "items": "Delivered items sold.",
    "wape": (
        "Weighted absolute percentage error: total absolute forecast error divided by total "
        "actual units. Lower is better."
    ),
    "bias": "Signed forecast error as a share of actuals. Negative means under-forecasting.",
}

INCOMPLETE_NOTE = (
    "Months marked incomplete extend past the date through which purchases are fully "
    "captured, so their totals are understated. Do not read them as a decline."
)
