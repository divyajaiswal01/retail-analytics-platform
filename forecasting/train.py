"""Train, backtest and forecast weekly demand per category.

Run from the project root:  python -m forecasting.train        (or: make forecast)
Close Jupyter / other DuckDB sessions first: results are written to the ``forecast`` schema.

Steps: load and validate demand -> walk-forward backtest of every model -> pick a model per
category on the earliest origins -> report honest accuracy on later holdout origins ->
fit on all data and forecast the next weeks -> write tables -> (optionally) log to MLflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from forecasting.backtest import (
    Forecaster,
    accuracy_table,
    interval_coverage,
    make_origins,
    policy_rows,
    residual_quantiles,
    run_backtest,
    select_models,
    split_origins,
)
from forecasting.baselines import moving_average, naive, seasonal_naive
from forecasting.config import (
    BASELINE_MODELS,
    CANDIDATE_MODELS,
    DEFAULT_CONFIG,
    ETS,
    LIGHTGBM,
    MOVING_AVERAGE,
    NAIVE,
    OUTPUT_SCHEMA,
    SEASONAL_NAIVE,
    SELECTED,
    ForecastConfig,
)
from forecasting.data import ForecastDataError, load_weekly_demand, to_matrix, validate_panel
from forecasting.metrics import summarize, wape
from forecasting.models import ets_forecast, lightgbm_forecast
from ingestion.config import get_warehouse_path
from ingestion.logger import get_logger

log = get_logger("forecasting")


def build_forecasters(config: ForecastConfig) -> dict[str, Forecaster]:
    """All models compared in the backtest, keyed by output name."""
    return {
        NAIVE: naive,
        MOVING_AVERAGE: moving_average,
        SEASONAL_NAIVE: partial(seasonal_naive, period=config.seasonal_period),
        ETS: ets_forecast,
        LIGHTGBM: partial(lightgbm_forecast, seed=config.seed),
    }


def build_final_forecast(
    y: np.ndarray,
    weeks: pd.DatetimeIndex,
    categories: list[str],
    forecasters: dict[str, Forecaster],
    choices: pd.DataFrame,
    quantiles: pd.DataFrame,
    horizon: int,
) -> pd.DataFrame:
    """Fit on all history, forecast the next ``horizon`` weeks with each category's chosen model."""
    needed = {*BASELINE_MODELS, *CANDIDATE_MODELS}
    all_forecasts = {name: forecasters[name](y, horizon) for name in needed}
    chosen = choices.set_index("category")["chosen_model"]
    qlow = quantiles.set_index("category")["q_low"]
    qhigh = quantiles.set_index("category")["q_high"]
    rows = []
    for j, category in enumerate(categories):
        model = str(chosen[category])
        point = all_forecasts[model][:, j]
        # Error band from backtest residuals; clamped so it always contains the point forecast.
        lower = np.clip(np.minimum(point * (1 + qlow[category]), point), 0, None)
        upper = np.maximum(point * (1 + qhigh[category]), point)
        for h in range(horizon):
            rows.append(
                {
                    "category": category,
                    "week_start": weeks[-1] + pd.Timedelta(weeks=h + 1),
                    "horizon": h + 1,
                    "model": model,
                    "forecast_units": float(point[h]),
                    "lower_units": float(lower[h]),
                    "upper_units": float(upper[h]),
                }
            )
    return pd.DataFrame(rows)


def build_uncertainty(
    forecast: pd.DataFrame,
    category_accuracy: pd.DataFrame,
    choices: pd.DataFrame,
    y: np.ndarray,
    categories: list[str],
    horizon: int,
) -> pd.DataFrame:
    """One row per category summarising how reliable its forecast is."""
    holdout = category_accuracy[category_accuracy["model"] == SELECTED].set_index("category")
    width = (
        forecast.assign(
            rel_width=(forecast["upper_units"] - forecast["lower_units"])
            / np.maximum(forecast["forecast_units"], 1.0)
        )
        .groupby("category")["rel_width"]
        .median()
    )
    total_forecast = forecast.groupby("category")["forecast_units"].sum()
    recent_actual = dict(zip(categories, y[-horizon:].sum(axis=0), strict=True))
    chosen = choices.set_index("category")["chosen_model"]
    rows = []
    for rank, category in enumerate(categories, start=1):
        recent = float(recent_actual[category])
        rows.append(
            {
                "category": category,
                "revenue_rank": rank,
                "chosen_model": chosen[category],
                "holdout_wape": holdout["wape"].get(category, float("nan")),
                "holdout_bias": holdout["bias"].get(category, float("nan")),
                "median_relative_interval_width": float(width[category]),
                "forecast_units": float(total_forecast[category]),
                "actual_units_last_period": recent,
                "change_vs_last_period_pct": (
                    100 * (float(total_forecast[category]) / recent - 1)
                    if recent > 0
                    else float("nan")
                ),
            }
        )
    out = pd.DataFrame(rows)
    out["uncertainty_rank"] = (
        out["holdout_wape"].rank(ascending=False, method="min").astype("Int64")
    )
    return out


def write_outputs(db_path: Path, tables: dict[str, pd.DataFrame]) -> None:
    """Replace each table in the ``forecast`` schema (idempotent)."""
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {OUTPUT_SCHEMA}")
        for name, frame in tables.items():
            con.register("_frame", frame)
            con.execute(f"CREATE OR REPLACE TABLE {OUTPUT_SCHEMA}.{name} AS SELECT * FROM _frame")
            con.unregister("_frame")
            log.info("Wrote %s.%s (%d rows)", OUTPUT_SCHEMA, name, len(frame))
    finally:
        con.close()


def log_to_mlflow(config: ForecastConfig, tables: dict[str, pd.DataFrame], n_origins: int) -> None:
    """Best-effort experiment tracking. A tracking failure is logged and never stops the run."""
    try:
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
        mlflow.set_experiment("weekly_category_demand")
        with mlflow.start_run(run_name=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")):
            mlflow.log_params({**asdict(config), "n_origins": n_origins})
            summary = tables["accuracy_summary"]
            holdout = summary[summary["scope"] == "holdout_origins"]
            for _, row in holdout.iterrows():
                mlflow.log_metric(f"holdout_wape_{row['model']}", float(row["wape"]))
                mlflow.log_metric(f"holdout_bias_{row['model']}", float(row["bias"]))
        log.info("Logged run to MLflow")
    except Exception as exc:  # noqa: BLE001 - tracking is optional; report and carry on
        log.warning("MLflow logging failed and was skipped: %s", exc)


def run(
    db_path: Path | None = None,
    config: ForecastConfig = DEFAULT_CONFIG,
    use_mlflow: bool = True,
) -> dict[str, pd.DataFrame]:
    """Run the full pipeline and return every output table."""
    path = db_path or get_warehouse_path()
    started = time.perf_counter()

    demand = load_weekly_demand(path, config.top_n)
    validate_panel(demand)
    y, weeks, categories = to_matrix(demand)
    if config.trim_last_weeks:
        if config.trim_last_weeks >= y.shape[0]:
            raise ValueError("trim_last_weeks removes the entire history.")
        y = y[: -config.trim_last_weeks]
        weeks = weeks[: -config.trim_last_weeks]
        log.warning(
            "Trimmed the newest %d week(s) from the history; the last week used is %s",
            config.trim_last_weeks,
            weeks[-1].date(),
        )
    n_weeks, n_cats = y.shape
    log.info(
        "Loaded demand | categories=%d | weeks=%d | %s to %s",
        n_cats,
        n_weeks,
        weeks[0].date(),
        weeks[-1].date(),
    )

    origins = make_origins(n_weeks, config.horizon, config.min_train_weeks, config.origin_step)
    selection_origins, holdout_origins = split_origins(origins, config.selection_fraction)
    log.info(
        "Backtest | origins=%d (selection=%d, holdout=%d) | horizon=%d weeks",
        len(origins),
        len(selection_origins),
        len(holdout_origins),
        config.horizon,
    )

    forecasters = build_forecasters(config)
    bt = run_backtest(y, weeks, categories, forecasters, origins, config.horizon)
    candidates: tuple[str, ...] = CANDIDATE_MODELS
    if not config.per_category_candidates:
        sel_rows = bt[bt["origin_idx"].isin(selection_origins)]
        pooled = {
            m: wape(
                sel_rows.loc[sel_rows["model"] == m, "actual"].to_numpy(dtype=np.float64),
                sel_rows.loc[sel_rows["model"] == m, "forecast"].to_numpy(dtype=np.float64),
            )
            for m in CANDIDATE_MODELS
        }
        best_global = min(pooled, key=lambda m: pooled[m])
        candidates = (best_global,)
        log.info(
            "Global candidate on selection origins: %s (%s)",
            best_global,
            ", ".join(f"{m}={w:.3f}" for m, w in pooled.items()),
        )
    choices = select_models(
        bt, selection_origins, candidates=candidates, margin=config.selection_margin
    )
    policy = policy_rows(bt, choices)
    bt_with_policy = pd.concat([bt, policy], ignore_index=True)

    holdout_rows = bt_with_policy[bt_with_policy["origin_idx"].isin(holdout_origins)]
    peak = bt[
        (bt["target_week"] >= pd.Timestamp(config.peak_start))
        & (bt["target_week"] <= pd.Timestamp(config.peak_end))
    ]
    full_year = bt[bt["origin_idx"] >= config.seasonal_period - 1]
    scopes = {
        "all_origins": bt,
        "holdout_origins": holdout_rows,
        "peak_weeks": peak,
        "full_year_origins": full_year,
    }
    accuracy_summary = pd.concat(
        [
            accuracy_table(frame).assign(scope=scope)
            for scope, frame in scopes.items()
            if len(frame)
        ],
        ignore_index=True,
    )
    if peak.empty:
        log.warning(
            "No backtest rows fall in the peak period %s to %s", config.peak_start, config.peak_end
        )
    category_accuracy = summarize(holdout_rows.dropna(subset=["forecast"]), ["category", "model"])
    horizon_accuracy = summarize(holdout_rows.dropna(subset=["forecast"]), ["model", "horizon"])

    quantiles = residual_quantiles(policy, config.interval_low, config.interval_high)
    # Honest check of the error bands: build them from selection origins only, test on holdout.
    sel_quantiles = residual_quantiles(
        policy[policy["origin_idx"].isin(selection_origins)],
        config.interval_low,
        config.interval_high,
    )
    coverage = interval_coverage(policy[policy["origin_idx"].isin(holdout_origins)], sel_quantiles)
    log.info(
        "Error band coverage on holdout: %.1f%% (target about %.0f%%)",
        coverage,
        100 * (config.interval_high - config.interval_low),
    )
    forecast = build_final_forecast(
        y, weeks, categories, forecasters, choices, quantiles, config.horizon
    )
    uncertainty = build_uncertainty(
        forecast, category_accuracy, choices, y, categories, config.horizon
    )

    run_log = pd.DataFrame(
        [
            {
                "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "config_json": json.dumps(asdict(config)),
                "categories": n_cats,
                "weeks": n_weeks,
                "first_week": weeks[0],
                "last_week": weeks[-1],
                "origins": len(origins),
                "selection_origins": len(selection_origins),
                "holdout_origins": len(holdout_origins),
                "holdout_interval_coverage_pct": coverage,
            }
        ]
    )
    tables = {
        "weekly_forecast": forecast,
        "backtest_results": bt_with_policy,
        "model_selection": choices,
        "accuracy_summary": accuracy_summary,
        "category_accuracy": category_accuracy,
        "horizon_accuracy": horizon_accuracy,
        "category_uncertainty": uncertainty,
        "run_log": run_log,
    }
    write_outputs(path, tables)
    if use_mlflow:
        log_to_mlflow(config, tables, len(origins))

    hold = accuracy_summary[accuracy_summary["scope"] == "holdout_origins"].set_index("model")[
        "wape"
    ]
    log.info(
        "Holdout WAPE | %s",
        " | ".join(f"{m}={w:.3f}" for m, w in hold.items()),
    )
    log.info("Forecasting complete | %.1fs", time.perf_counter() - started)
    return tables


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code (0 = success)."""
    parser = argparse.ArgumentParser(description="Weekly category demand forecasting")
    parser.add_argument("--top-n", type=int, default=DEFAULT_CONFIG.top_n)
    parser.add_argument("--horizon", type=int, default=DEFAULT_CONFIG.horizon)
    parser.add_argument(
        "--trim-last-weeks",
        type=int,
        default=DEFAULT_CONFIG.trim_last_weeks,
        help="drop the newest N weeks from the history (use if the last week looks incomplete)",
    )
    parser.add_argument("--no-mlflow", action="store_true", help="skip MLflow tracking")
    args = parser.parse_args(argv)
    config = replace(
        DEFAULT_CONFIG,
        top_n=args.top_n,
        horizon=args.horizon,
        trim_last_weeks=args.trim_last_weeks,
    )
    try:
        run(config=config, use_mlflow=not args.no_mlflow)
    except (ForecastDataError, ValueError) as exc:
        log.error("Forecasting failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
