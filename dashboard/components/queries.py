"""Named queries. Every query only reads gold (``marts``) or ``forecast`` tables.

There is no business logic here: revenue, on-time, retention and the rest are defined in dbt
(see docs/kpi_definitions.md). The dashboard selects, filters and displays.
"""

from __future__ import annotations

import pandas as pd

from dashboard.components.data import load


# ---------------------------------------------------------------- marts
def summary() -> pd.DataFrame:
    return load(
        """
        SELECT window_start, window_end, data_complete_through, delivered_orders,
               delivered_revenue, aov, customers, repeat_customers, repeat_rate_pct,
               on_time_pct, avg_delivery_days, avg_review_score
        FROM marts.metrics_summary
        """
    )


def monthly_kpis() -> pd.DataFrame:
    return load(
        """
        SELECT year_month, orders_placed, delivered_orders, delivered_revenue, aov,
               freight_total, unique_customers, new_customers, returning_customers,
               on_time_pct, avg_delivery_days, avg_review_score, revenue_mom_growth_pct,
               is_complete_month
        FROM marts.metrics_kpis ORDER BY year_month
        """
    )


def categories() -> pd.DataFrame:
    return load(
        """
        SELECT revenue_rank, category, items_sold, orders, revenue, avg_price,
               revenue_share_pct, cumulative_share_pct, revenue_current_period,
               revenue_prior_period, yoy_growth_pct
        FROM marts.mart_category_performance ORDER BY revenue_rank
        """
    )


def states() -> pd.DataFrame:
    return load(
        """
        SELECT state, customers, delivered_orders, delivered_revenue, aov,
               revenue_share_pct, on_time_pct, avg_delivery_days, avg_review_score
        FROM marts.mart_state_performance ORDER BY delivered_revenue DESC
        """
    )


def delivery_impact() -> pd.DataFrame:
    return load(
        """
        SELECT bucket_order, delivery_bucket, orders, avg_review_score, pct_low_reviews,
               pct_five_star, avg_delivery_days
        FROM marts.mart_delivery_impact ORDER BY bucket_order
        """
    )


def delivery_vs_repeat() -> pd.DataFrame:
    return load(
        """
        SELECT first_delivery, customers, repeat_customers, repeat_rate_pct,
               avg_first_review_score
        FROM marts.mart_delivery_vs_repeat ORDER BY first_delivery
        """
    )


def sellers() -> pd.DataFrame:
    return load(
        """
        SELECT seller_key, state, orders, revenue, late_pct, avg_delivery_days,
               avg_review_score, reviewed_orders, meets_min_volume, overall_late_pct,
               overall_avg_review_score
        FROM marts.mart_seller_performance
        """
    )


def sales_cube() -> pd.DataFrame:
    return load(
        """
        SELECT year_month, category, state, items_sold, revenue, is_complete_month
        FROM marts.mart_sales_cube
        """
    )


def weekly_demand() -> pd.DataFrame:
    return load(
        """
        SELECT week_start, category, units, category_revenue_rank
        FROM marts.mart_weekly_category_demand ORDER BY week_start
        """
    )


# ---------------------------------------------------------------- forecast
def forecast_run() -> pd.DataFrame:
    return load(
        """
        SELECT run_at_utc, categories, weeks, first_week, last_week, origins,
               selection_origins, holdout_origins, holdout_interval_coverage_pct
        FROM forecast.run_log
        """
    )


def forecast() -> pd.DataFrame:
    return load(
        """
        SELECT category, week_start, horizon, model, forecast_units, lower_units, upper_units
        FROM forecast.weekly_forecast ORDER BY category, week_start
        """
    )


def forecast_all_models() -> pd.DataFrame:
    return load(
        """
        SELECT category, week_start, horizon, model, forecast_units
        FROM forecast.weekly_forecast_all_models ORDER BY category, model, week_start
        """
    )


def accuracy_summary() -> pd.DataFrame:
    return load(
        """
        SELECT scope, model, rows, coverage_pct, wape, bias, mae, median_category_wape
        FROM forecast.accuracy_summary
        """
    )


def horizon_accuracy() -> pd.DataFrame:
    return load("SELECT model, horizon, wape, bias FROM forecast.horizon_accuracy")


def uncertainty() -> pd.DataFrame:
    return load(
        """
        SELECT category, revenue_rank, chosen_model, holdout_wape, holdout_bias,
               median_relative_interval_width, forecast_units, actual_units_last_period,
               change_vs_last_period_pct, uncertainty_rank
        FROM forecast.category_uncertainty ORDER BY uncertainty_rank
        """
    )
