"""Page tests for the Streamlit dashboard, run headlessly with Streamlit's AppTest.

A small warehouse is built from known numbers, so the tests can check that what is shown on
screen equals what is stored, that filters add up, and that failures show a clear message
instead of a stack trace.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "router": "dashboard/app.py",
    "overview": "dashboard/pages/1_Executive_Overview.py",
    "drilldown": "dashboard/pages/2_Category_Drilldown.py",
    "delivery": "dashboard/pages/3_Delivery_Performance.py",
    "forecast": "dashboard/pages/4_Forecast.py",
}
MONTHS = ["2018-05", "2018-06", "2018-07", "2018-08"]
CATEGORIES = ["health_beauty", "toys", "auto"]
STATES = ["SP", "RJ", "MG"]
TOTAL_REVENUE = 150_000.0


def _write(con: duckdb.DuckDBPyConnection, schema: str, name: str, frame: pd.DataFrame) -> None:
    con.register("_f", frame)
    con.execute(f"CREATE OR REPLACE TABLE {schema}.{name} AS SELECT * FROM _f")
    con.unregister("_f")


def build_warehouse(path: Path) -> None:
    """Create every table the dashboard reads, with small, known values."""
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE SCHEMA forecast")

    _write(con, "marts", "metrics_summary", pd.DataFrame([{
        "window_start": date(2018, 1, 1), "window_end": date(2018, 8, 31),
        "data_complete_through": date(2018, 8, 19), "delivered_orders": 1000,
        "delivered_revenue": TOTAL_REVENUE, "aov": 150.0, "customers": 950,
        "repeat_customers": 30, "repeat_rate_pct": 3.16, "on_time_pct": 92.5,
        "avg_delivery_days": 12.0, "avg_review_score": 4.1,
    }]))  # fmt: skip

    _write(con, "marts", "metrics_kpis", pd.DataFrame([
        {
            "year_month": m, "orders_placed": 260, "delivered_orders": 250,
            "delivered_revenue": 37_500.0, "aov": 150.0, "freight_total": 4000.0,
            "unique_customers": 240, "new_customers": 230, "returning_customers": 10,
            "on_time_pct": 92.0, "avg_delivery_days": 12.0, "avg_review_score": 4.1,
            "revenue_mom_growth_pct": 1.5, "is_complete_month": m != "2018-08",
        }
        for m in MONTHS
    ]))  # fmt: skip

    _write(con, "marts", "mart_category_performance", pd.DataFrame([
        {
            "revenue_rank": i, "category": c, "items_sold": 500 - 100 * i, "orders": 400 - 80 * i,
            "revenue": 60_000.0 - 15_000 * i, "avg_price": 100.0,
            "revenue_share_pct": 40.0 - 10 * i,
            "cumulative_share_pct": 40.0 * i, "revenue_current_period": 1.0,
            "revenue_prior_period": 1.0, "yoy_growth_pct": 10.0,
        }
        for i, c in enumerate(CATEGORIES, start=1)
    ]))  # fmt: skip

    _write(con, "marts", "mart_state_performance", pd.DataFrame([
        {
            "state": s, "customers": 300 - 50 * i, "delivered_orders": 400 - 100 * i,
            "delivered_revenue": 60_000.0 - 20_000 * i, "aov": 150.0,
            "revenue_share_pct": 40.0 - 10 * i, "on_time_pct": 95.0 - 4 * i,
            "avg_delivery_days": 10.0 + 3 * i, "avg_review_score": 4.3 - 0.2 * i,
        }
        for i, s in enumerate(STATES)
    ]))  # fmt: skip

    buckets = [
        "on time or early",
        "1-3 days late",
        "4-7 days late",
        "8-14 days late",
        "15+ days late",
    ]
    _write(con, "marts", "mart_delivery_impact", pd.DataFrame([
        {
            "bucket_order": i, "delivery_bucket": b, "orders": 1000 // i,
            "avg_review_score": 4.5 - 0.7 * i, "pct_low_reviews": 8.0 * i,
            "pct_five_star": 70.0 / i, "avg_delivery_days": 10.0 * i,
        }
        for i, b in enumerate(buckets, start=1)
    ]))  # fmt: skip

    _write(con, "marts", "mart_delivery_vs_repeat", pd.DataFrame([
        {"first_delivery": "late", "customers": 400, "repeat_customers": 6,
         "repeat_rate_pct": 1.5, "avg_first_review_score": 2.4},
        {"first_delivery": "on time or early", "customers": 5000, "repeat_customers": 100,
         "repeat_rate_pct": 2.0, "avg_first_review_score": 4.3},
    ]))  # fmt: skip

    _write(con, "marts", "mart_seller_performance", pd.DataFrame([
        {
            "seller_key": f"s{i}", "state": "SP", "orders": 80 - 10 * i, "revenue": 9000.0,
            "late_pct": 5.0 + 4 * i, "avg_delivery_days": 12.0, "avg_review_score": 4.5 - 0.3 * i,
            "reviewed_orders": 70, "meets_min_volume": i < 4,
            "overall_late_pct": 8.1, "overall_avg_review_score": 4.16,
        }
        for i in range(5)
    ]))  # fmt: skip

    cube = [
        {
            "year_month": m, "category": c, "state": s,
            "items_sold": 10 + 2 * ci + si, "revenue": 1000.0 * (ci + 1) + 100.0 * si,
            "is_complete_month": m != "2018-08",
        }
        for m in MONTHS for ci, c in enumerate(CATEGORIES) for si, s in enumerate(STATES)
    ]  # fmt: skip
    _write(con, "marts", "mart_sales_cube", pd.DataFrame(cube))

    weeks = pd.date_range("2018-01-01", periods=30, freq="7D")
    _write(con, "marts", "mart_weekly_category_demand", pd.DataFrame([
        {"week_start": w.date(), "category": c, "units": 50 - 10 * r + (i % 5),
         "category_revenue_rank": r}
        for r, c in enumerate(CATEGORIES, start=1) for i, w in enumerate(weeks)
    ]))  # fmt: skip

    future = pd.date_range(weeks[-1] + pd.Timedelta(weeks=1), periods=4, freq="7D")
    _write(con, "forecast", "run_log", pd.DataFrame([{
        "run_at_utc": "2026-10-20 22:25:56", "categories": 3, "weeks": 30,
        "first_week": weeks[0], "last_week": weeks[-1], "origins": 12, "selection_origins": 8,
        "holdout_origins": 4, "holdout_interval_coverage_pct": 71.7,
    }]))  # fmt: skip
    fc, all_models = [], []
    for r, c in enumerate(CATEGORIES, start=1):
        for h, w in enumerate(future, start=1):
            base = 50 - 10 * r
            fc.append({
                "category": c, "week_start": w, "horizon": h, "model": "naive",
                "forecast_units": float(base), "lower_units": base * 0.7,
                "upper_units": base * 1.3,
            })  # fmt: skip
            for model in ("naive", "moving_average_4", "ets", "lightgbm"):
                all_models.append({"category": c, "week_start": w, "horizon": h, "model": model,
                                   "forecast_units": float(base)})  # fmt: skip
    _write(con, "forecast", "weekly_forecast", pd.DataFrame(fc))
    _write(con, "forecast", "weekly_forecast_all_models", pd.DataFrame(all_models))

    scopes = ["holdout_origins", "all_origins", "full_year_origins", "peak_weeks"]
    models = ["naive", "moving_average_4", "ets", "lightgbm", "seasonal_naive_52"]
    _write(con, "forecast", "accuracy_summary", pd.DataFrame([
        {"scope": sc, "model": m, "rows": 100, "coverage_pct": 100.0, "wape": 0.25 + 0.03 * mi,
         "bias": 0.01 * mi, "mae": 20.0, "median_category_wape": 0.26}
        for sc in scopes for mi, m in enumerate(models)
    ]))  # fmt: skip
    _write(con, "forecast", "horizon_accuracy", pd.DataFrame([
        {"model": m, "horizon": h, "wape": 0.2 + 0.02 * h, "bias": 0.0}
        for m in models for h in range(1, 5)
    ]))  # fmt: skip
    _write(con, "forecast", "category_uncertainty", pd.DataFrame([
        {
            "category": c, "revenue_rank": r, "chosen_model": "naive",
            "holdout_wape": 0.2 + 0.1 * r,
            "holdout_bias": 0.0, "median_relative_interval_width": 0.9, "forecast_units": 160.0,
            "actual_units_last_period": 150.0, "change_vs_last_period_pct": 6.7,
            "uncertainty_rank": 4 - r,
        }
        for r, c in enumerate(CATEGORIES, start=1)
    ]))  # fmt: skip
    con.close()


@pytest.fixture
def warehouse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "wh.duckdb"
    build_warehouse(path)
    monkeypatch.setenv("WAREHOUSE_PATH", str(path))
    return path


def open_page(name: str) -> AppTest:
    return AppTest.from_file(str(ROOT / PAGES[name]), default_timeout=60).run()


# ---------------------------------------------------------------- rendering
@pytest.mark.parametrize("name", list(PAGES))
def test_every_page_renders_without_errors(warehouse: Path, name: str) -> None:
    at = open_page(name)
    assert not at.exception
    assert not at.error


def test_overview_shows_stored_numbers(warehouse: Path) -> None:
    at = open_page("overview")
    cards = {m.label: m.value for m in at.metric}
    assert cards["Delivered revenue"] == "R$ 150.0K"
    assert cards["Delivered orders"] == "1,000"
    assert cards["Average order value"] == "R$ 150.00"
    assert cards["On-time delivery"] == "92.5%"
    assert cards["Repeat rate"] == "3.16%"


def test_dates_are_shown_without_timestamps(warehouse: Path) -> None:
    banner = open_page("overview").info[0].value
    assert "2018-01-01" in banner and "2018-08-19" in banner
    assert "00:00:00" not in banner


# ---------------------------------------------------------------- drill-down
def cube_revenue(states: list[str] | None = None) -> float:
    total = 0.0
    for ci in range(len(CATEGORIES)):
        for si, s in enumerate(STATES):
            if states is None or s in states:
                total += len(MONTHS) * (1000.0 * (ci + 1) + 100.0 * si)
    return total


def test_drilldown_filters_add_up(warehouse: Path) -> None:
    at = open_page("drilldown")
    at.multiselect[0].set_value(CATEGORIES).run()  # all categories
    assert at.metric[0].value == f"R$ {cube_revenue() / 1000:,.1f}K"
    assert at.metric[2].value == "100.0%"

    at.multiselect[1].set_value(["SP"]).run()
    assert at.metric[0].value == f"R$ {cube_revenue(['SP']) / 1000:,.1f}K"
    expected_share = 100 * cube_revenue(["SP"]) / cube_revenue()
    assert at.metric[2].value == f"{expected_share:,.1f}%"
    assert not at.exception


def test_drilldown_empty_selection_shows_a_message(warehouse: Path) -> None:
    at = open_page("drilldown")
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert any("Select at least one" in i.value for i in at.info)


# ---------------------------------------------------------------- forecast
def test_forecast_tabs_and_category_switch(warehouse: Path) -> None:
    at = open_page("forecast")
    assert len(at.tabs) == 4
    at.selectbox[0].set_value("toys").run()
    assert not at.exception
    assert at.metric[0].value == "naive"


def test_forecast_every_evaluation_set_works(warehouse: Path) -> None:
    at = open_page("forecast")
    box = next(sb for sb in at.selectbox if sb.label == "Evaluation set")
    for scope in list(box.options):
        box.set_value(scope)
        at.run()
        assert not at.exception


def test_forecast_shows_band_coverage_from_the_run_log(warehouse: Path) -> None:
    at = open_page("forecast")
    coverage = next(m for m in at.metric if "coverage" in m.label.lower())
    assert coverage.value == "71.7%"


# ---------------------------------------------------------------- failure states
@pytest.mark.parametrize("name", list(PAGES))
def test_missing_warehouse_shows_a_message_not_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv("WAREHOUSE_PATH", str(tmp_path / "missing.duckdb"))
    at = open_page(name)
    assert not at.exception
    assert at.error and "Warehouse not found" in at.error[0].value


def test_missing_forecast_tables_only_affect_the_forecast_page(
    warehouse: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = tmp_path / "no_forecast.duckdb"
    shutil.copy(warehouse, broken)
    con = duckdb.connect(str(broken))
    con.execute("DROP SCHEMA forecast CASCADE")
    con.close()
    monkeypatch.setenv("WAREHOUSE_PATH", str(broken))

    forecast_page = open_page("forecast")
    assert not forecast_page.exception
    assert forecast_page.error and "missing" in forecast_page.error[0].value

    overview = open_page("overview")
    assert not overview.exception and not overview.error

    router = open_page("router")
    assert not router.exception
    assert any("not generated yet" in c.value for c in router.sidebar.caption)


def test_locked_warehouse_gives_a_helpful_message(
    warehouse: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    locked = tmp_path / "locked.duckdb"
    shutil.copy(warehouse, locked)
    writer = duckdb.connect(str(locked))  # holds the write lock, like a running dbt build
    try:
        monkeypatch.setenv("WAREHOUSE_PATH", str(locked))
        at = open_page("overview")
        assert not at.exception
        assert at.error and "could not be opened" in at.error[0].value
    finally:
        writer.close()


# ---------------------------------------------------------------- router and sidebar status
def test_router_opens_on_the_executive_overview(warehouse: Path) -> None:
    at = open_page("router")
    assert not at.exception and not at.error
    assert at.title[0].value == "Executive Overview"
    assert len(at.metric) == 8


def test_sidebar_shows_data_status_from_the_warehouse(warehouse: Path) -> None:
    captions = [c.value for c in open_page("router").sidebar.caption]
    assert any("Window: 2018-01-01 to 2018-08-31" in c for c in captions)
    assert any("Purchases complete through: 2018-08-19" in c for c in captions)
    assert any("Forecast generated: 2026-10-20 22:25:56 UTC" in c for c in captions)
