"""Rolling-origin backtesting, model selection, accuracy tables and error bands.

Backtesting is walk-forward only: at each origin a model sees weeks up to the origin and is scored
on the next ``horizon`` weeks. Origins are never shuffled and no model is ever given future data.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import numpy.typing as npt
import pandas as pd

from forecasting.config import BASELINE_MODELS, CANDIDATE_MODELS, SELECTED
from forecasting.metrics import summarize, wape

Array = npt.NDArray[np.float64]
Forecaster = Callable[[Array, int], Array]


def make_origins(n_weeks: int, horizon: int, min_train_weeks: int, step: int) -> list[int]:
    """Indices of the last training week for each backtest origin."""
    first = min_train_weeks - 1
    last = n_weeks - 1 - horizon  # the last origin must still have `horizon` weeks to score
    if last < first:
        raise ValueError(
            f"Not enough weeks ({n_weeks}) for min_train_weeks={min_train_weeks} "
            f"and horizon={horizon}."
        )
    return list(range(first, last + 1, step))


def split_origins(origins: list[int], selection_fraction: float) -> tuple[list[int], list[int]]:
    """Earliest origins pick the model; the remaining later origins are the honest holdout."""
    if len(origins) < 2:
        raise ValueError("Need at least two backtest origins to split selection from holdout.")
    n_selection = min(max(1, math.ceil(selection_fraction * len(origins))), len(origins) - 1)
    return origins[:n_selection], origins[n_selection:]


def run_backtest(
    y: Array,
    weeks: pd.DatetimeIndex,
    categories: list[str],
    forecasters: dict[str, Forecaster],
    origins: list[int],
    horizon: int,
) -> pd.DataFrame:
    """Forecast from every origin with every model.

    Returns one row per origin, model, category and horizon.
    """
    n_cats = y.shape[1]
    horizons = np.repeat(np.arange(1, horizon + 1), n_cats)
    cat_idx = np.tile(np.arange(n_cats), horizon)
    frames = []
    for origin in origins:
        history = y[: origin + 1].copy()  # nothing after the origin is passed to a model
        actual = y[origin + 1 : origin + 1 + horizon]
        for name, forecaster in forecasters.items():
            forecast = forecaster(history, horizon)
            if forecast.shape != (horizon, n_cats):
                raise ValueError(
                    f"{name} returned shape {forecast.shape}, expected {(horizon, n_cats)}"
                )
            frames.append(
                pd.DataFrame(
                    {
                        "origin_idx": origin,
                        "origin_week": weeks[origin],
                        "category": [categories[c] for c in cat_idx],
                        "horizon": horizons,
                        "target_week": weeks[origin + horizons],
                        "actual": actual.ravel(),
                        "model": name,
                        "forecast": forecast.ravel(),
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def select_models(
    bt: pd.DataFrame,
    selection_origins: list[int],
    baselines: tuple[str, ...] = BASELINE_MODELS,
    candidates: tuple[str, ...] = CANDIDATE_MODELS,
    margin: float = 0.05,
) -> pd.DataFrame:
    """Per category, pick the best candidate only if it beats the best baseline by ``margin``.

    Selection uses the selection origins only, so the holdout stays an honest test of the choice.
    """
    sel = bt[bt["origin_idx"].isin(selection_origins)]
    rows = []
    for category, g in sel.groupby("category", sort=False):
        scores = {
            str(model): wape(
                gm["actual"].to_numpy(dtype=np.float64), gm["forecast"].to_numpy(dtype=np.float64)
            )
            for model, gm in g.groupby("model")
            if model in (*baselines, *candidates)
        }
        base = {m: scores[m] for m in baselines if not math.isnan(scores.get(m, float("nan")))}
        cand = {m: scores[m] for m in candidates if not math.isnan(scores.get(m, float("nan")))}
        if not base:
            rows.append(
                {
                    "category": category,
                    "chosen_model": baselines[0],
                    "best_baseline": baselines[0],
                    "best_baseline_wape": float("nan"),
                    "best_candidate": None,
                    "best_candidate_wape": float("nan"),
                    "improvement_pct": float("nan"),
                    "reason": "no demand in the selection period; baseline used",
                }
            )
            continue
        best_base = min(base, key=lambda m: base[m])
        best_cand = min(cand, key=lambda m: cand[m]) if cand else None
        improvement = (
            1 - cand[best_cand] / base[best_base]
            if best_cand and base[best_base] > 0
            else float("nan")
        )
        use_candidate = best_cand is not None and cand[best_cand] <= base[best_base] * (1 - margin)
        chosen = best_cand if use_candidate and best_cand else best_base
        rows.append(
            {
                "category": category,
                "chosen_model": chosen,
                "best_baseline": best_base,
                "best_baseline_wape": base[best_base],
                "best_candidate": best_cand,
                "best_candidate_wape": cand[best_cand] if best_cand else float("nan"),
                "improvement_pct": 100 * improvement,
                "reason": (
                    f"{best_cand} beats {best_base} by at least {margin:.0%}"
                    if use_candidate
                    else f"no candidate beats {best_base} by {margin:.0%}; baseline fallback"
                ),
            }
        )
    return pd.DataFrame(rows)


def policy_rows(bt: pd.DataFrame, choices: pd.DataFrame) -> pd.DataFrame:
    """Backtest rows of each category's chosen model, relabelled as the ``selected`` policy."""
    merged = bt.merge(choices[["category", "chosen_model"]], on="category")
    chosen = merged[merged["model"] == merged["chosen_model"]].copy()
    chosen["model"] = SELECTED
    return chosen[list(bt.columns)].reset_index(drop=True)


def accuracy_table(df: pd.DataFrame) -> pd.DataFrame:
    """Pooled and per-category accuracy per model, with how much of the data each model covers."""
    total_rows = df.groupby("model").size()
    usable = df.dropna(subset=["forecast"])
    pooled = summarize(usable, ["model"])
    per_category = summarize(usable, ["model", "category"])
    median_cat = per_category.groupby("model")["wape"].median().rename("median_category_wape")
    out = pooled.merge(median_cat, on="model")
    out["coverage_pct"] = 100 * out["rows"] / out["model"].map(total_rows)
    return out[["model", "rows", "coverage_pct", "wape", "bias", "mae", "median_category_wape"]]


def interval_coverage(policy: pd.DataFrame, quantiles: pd.DataFrame) -> float:
    """Share (%) of actuals inside the error band built from ``quantiles``."""
    merged = policy.merge(quantiles, on="category")
    scale = np.maximum(merged["forecast"], 1.0)
    lower = merged["forecast"] + merged["q_low"] * scale
    upper = merged["forecast"] + merged["q_high"] * scale
    inside = (merged["actual"] >= np.minimum(lower, merged["forecast"])) & (
        merged["actual"] <= np.maximum(upper, merged["forecast"])
    )
    return float(100 * inside.mean())


def residual_quantiles(policy: pd.DataFrame, low: float, high: float) -> pd.DataFrame:
    """Per category, quantiles of relative error: (actual - forecast) / max(forecast, 1)."""
    rel = (policy["actual"] - policy["forecast"]) / np.maximum(policy["forecast"], 1.0)
    frame = policy.assign(rel_error=rel)
    q = frame.groupby("category", sort=False)["rel_error"]
    return pd.DataFrame({"q_low": q.quantile(low), "q_high": q.quantile(high)}).reset_index()
