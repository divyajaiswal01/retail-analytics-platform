"""End-to-end test of forecasting/train.py on a small synthetic warehouse."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from forecasting.config import DEFAULT_CONFIG, OUTPUT_SCHEMA, SELECTED
from forecasting.data import ForecastDataError, load_weekly_demand
from forecasting.train import main, run

N_WEEKS = 62
CATEGORIES = ["big", "medium", "small", "tiny"]


def build_warehouse(path: Path, n_weeks: int = N_WEEKS) -> None:
    """Create marts.mart_weekly_category_demand with trending, noisy demand."""
    rng = np.random.default_rng(11)
    weeks = pd.date_range("2017-01-02", periods=n_weeks, freq="7D")
    rows = []
    for rank, (category, size) in enumerate(zip(CATEGORIES, [30, 12, 6, 2], strict=True), start=1):
        level = size * np.linspace(0.6, 1.4, n_weeks)
        for week, mean in zip(weeks, level, strict=True):
            units = int(rng.poisson(mean))
            rows.append(
                {
                    "demand_key": f"{category}|{week.date()}",
                    "week_start": week.date(),
                    "category": category,
                    "units": units,
                    "orders": units,
                    "revenue": units * 100.0,
                    "category_revenue_rank": rank,
                }
            )
    frame = pd.DataFrame(rows)
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA marts")
    con.register("f", frame)
    con.execute("CREATE TABLE marts.mart_weekly_category_demand AS SELECT * FROM f")
    con.close()


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    path = tmp_path / "wh.duckdb"
    build_warehouse(path)
    return path


FAST = replace(DEFAULT_CONFIG, top_n=4, horizon=4, min_train_weeks=26, origin_step=4)


def test_pipeline_writes_all_tables(warehouse: Path) -> None:
    tables = run(db_path=warehouse, config=FAST, use_mlflow=False)
    expected = {
        "weekly_forecast",
        "weekly_forecast_all_models",
        "backtest_results",
        "model_selection",
        "accuracy_summary",
        "category_accuracy",
        "horizon_accuracy",
        "category_uncertainty",
        "run_log",
    }
    assert set(tables) == expected

    con = duckdb.connect(str(warehouse), read_only=True)
    stored = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
            [OUTPUT_SCHEMA],
        ).fetchall()
    }
    con.close()
    assert expected <= stored


def test_forecast_table_is_complete_and_valid(warehouse: Path) -> None:
    forecast = run(db_path=warehouse, config=FAST, use_mlflow=False)["weekly_forecast"]
    assert len(forecast) == 4 * 4  # categories x horizon
    assert (forecast["forecast_units"] >= 0).all()
    assert (forecast["lower_units"] <= forecast["forecast_units"] + 1e-9).all()
    assert (forecast["upper_units"] >= forecast["forecast_units"] - 1e-9).all()
    assert forecast["week_start"].min() > pd.Timestamp("2017-01-02") + pd.Timedelta(
        weeks=N_WEEKS - 1
    )


def test_holdout_is_reported_for_the_selected_policy(warehouse: Path) -> None:
    summary = run(db_path=warehouse, config=FAST, use_mlflow=False)["accuracy_summary"]
    holdout = summary[summary["scope"] == "holdout_origins"]
    assert SELECTED in set(holdout["model"])
    assert {"naive", "moving_average_4", "ets", "lightgbm"} <= set(holdout["model"])


def test_rerun_is_idempotent(warehouse: Path) -> None:
    first = run(db_path=warehouse, config=FAST, use_mlflow=False)["weekly_forecast"]
    second = run(db_path=warehouse, config=FAST, use_mlflow=False)["weekly_forecast"]
    pd.testing.assert_frame_equal(first, second)
    con = duckdb.connect(str(warehouse), read_only=True)
    rows = con.execute(f"SELECT COUNT(*) FROM {OUTPUT_SCHEMA}.weekly_forecast").fetchone()
    con.close()
    assert rows is not None and rows[0] == len(first)  # replaced, not appended


def test_missing_table_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "empty.duckdb"
    duckdb.connect(str(path)).close()
    with pytest.raises(ForecastDataError, match="dbt build"):
        load_weekly_demand(path, 4)


def test_missing_warehouse_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(ForecastDataError, match="not found"):
        load_weekly_demand(tmp_path / "nope.duckdb", 4)


def test_cli_returns_nonzero_on_bad_input(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WAREHOUSE_PATH", str(tmp_path / "missing.duckdb"))
    assert main(["--no-mlflow"]) == 1


def test_trim_last_weeks_removes_newest_history(warehouse: Path) -> None:
    config = replace(FAST, trim_last_weeks=2)
    tables = run(db_path=warehouse, config=config, use_mlflow=False)
    run_log = tables["run_log"].iloc[0]
    assert run_log["weeks"] == N_WEEKS - 2
    last_used = pd.Timestamp("2017-01-02") + pd.Timedelta(weeks=N_WEEKS - 3)
    assert run_log["last_week"] == last_used
    # the first forecast week follows the last week that was kept
    assert tables["weekly_forecast"]["week_start"].min() == last_used + pd.Timedelta(weeks=1)


def test_trim_cannot_remove_everything(warehouse: Path) -> None:
    with pytest.raises(ValueError, match="entire history"):
        run(db_path=warehouse, config=replace(FAST, trim_last_weeks=N_WEEKS), use_mlflow=False)


def test_all_models_table_covers_every_model_and_matches_the_chosen_forecast(
    warehouse: Path,
) -> None:
    tables = run(db_path=warehouse, config=FAST, use_mlflow=False)
    models = tables["weekly_forecast_all_models"]
    assert {"naive", "moving_average_4", "ets", "lightgbm"} <= set(models["model"])
    assert len(models) == 4 * 4 * 4  # models x categories x horizon
    # the chosen forecast must equal that same model's row in the all-models table
    chosen = tables["weekly_forecast"].merge(
        models, on=["category", "week_start", "model"], suffixes=("", "_all")
    )
    assert len(chosen) == len(tables["weekly_forecast"])
    assert (chosen["forecast_units"] - chosen["forecast_units_all"]).abs().max() < 1e-9
