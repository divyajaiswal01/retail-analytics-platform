"""Tests for baselines, models, backtesting, selection and data validation.

The most important test is the counterfactual leakage check: changing weeks AFTER a forecast
origin must never change what a model forecasts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecasting.backtest import (
    interval_coverage,
    make_origins,
    policy_rows,
    residual_quantiles,
    run_backtest,
    select_models,
    split_origins,
)
from forecasting.baselines import moving_average, naive, seasonal_naive
from forecasting.config import SELECTED
from forecasting.data import ForecastDataError, to_matrix, validate_panel
from forecasting.models import ets_forecast, lightgbm_forecast


def make_series(n_weeks: int = 45, n_cats: int = 3, seed: int = 0) -> np.ndarray:
    """A trending, noisy demand matrix with categories of different sizes."""
    rng = np.random.default_rng(seed)
    trend = np.linspace(10, 30, n_weeks)[:, None]
    level = np.array([1.0, 0.5, 0.2])[:n_cats][None, :]
    return rng.poisson(trend * level).astype(np.float64)


# ---------------------------------------------------------------- baselines
def test_naive_repeats_last_week() -> None:
    y = np.array([[1.0, 5.0], [2.0, 6.0], [3.0, 7.0]])
    out = naive(y, 4)
    assert out.shape == (4, 2)
    assert (out == np.array([3.0, 7.0])).all()


def test_moving_average_uses_last_four_weeks() -> None:
    y = np.arange(1.0, 11.0).reshape(-1, 1)  # 1..10
    assert moving_average(y, 2)[0, 0] == pytest.approx(np.mean([7, 8, 9, 10]))


def test_seasonal_naive_is_nan_without_a_full_year() -> None:
    assert np.isnan(seasonal_naive(make_series(40), 8)).all()


def test_seasonal_naive_copies_same_week_last_year() -> None:
    y = np.arange(60.0).reshape(-1, 1)
    out = seasonal_naive(y, 3)
    # next week is index 60; one year (52 weeks) earlier is index 8
    assert out[:, 0].tolist() == [8.0, 9.0, 10.0]


# ---------------------------------------------------------------- origins
def test_make_origins_bounds() -> None:
    origins = make_origins(n_weeks=86, horizon=8, min_train_weeks=30, step=4)
    assert origins[0] == 29
    assert origins[-1] + 8 <= 85  # the last origin still has 8 weeks to score
    assert all(b - a == 4 for a, b in zip(origins, origins[1:], strict=False))


def test_make_origins_rejects_too_little_history() -> None:
    with pytest.raises(ValueError, match="Not enough weeks"):
        make_origins(n_weeks=20, horizon=8, min_train_weeks=30, step=4)


def test_split_origins_is_chronological_and_nonempty() -> None:
    selection, holdout = split_origins(list(range(13)), 0.6)
    assert selection and holdout
    assert max(selection) < min(holdout)  # holdout comes strictly after selection
    assert selection + holdout == list(range(13))


# ---------------------------------------------------------------- leakage
@pytest.mark.parametrize(
    "forecaster",
    [naive, moving_average, seasonal_naive, ets_forecast, lightgbm_forecast],
    ids=["naive", "moving_average", "seasonal_naive", "ets", "lightgbm"],
)
def test_forecasts_do_not_depend_on_the_future(forecaster) -> None:  # type: ignore[no-untyped-def]
    """Counterfactual: rewrite every week after the origin; forecasts must not change."""
    y = make_series(60)
    weeks = pd.date_range("2017-01-02", periods=60, freq="7D")
    cats = ["a", "b", "c"]
    origin = 40

    y_altered = y.copy()
    y_altered[origin + 1 :] = 9999.0  # wildly different future

    a = run_backtest(y, weeks, cats, {"m": forecaster}, [origin], 8)
    b = run_backtest(y_altered, weeks, cats, {"m": forecaster}, [origin], 8)
    pd.testing.assert_series_equal(a["forecast"], b["forecast"])
    assert not a["actual"].equals(b["actual"])  # the actuals did change, as intended


def test_backtest_targets_always_after_origin() -> None:
    y = make_series(50)
    weeks = pd.date_range("2017-01-02", periods=50, freq="7D")
    bt = run_backtest(y, weeks, ["a", "b", "c"], {"naive": naive}, [30, 34], 4)
    assert (bt["target_week"] > bt["origin_week"]).all()
    assert set(bt["horizon"]) == {1, 2, 3, 4}


# ---------------------------------------------------------------- models
def test_models_return_correct_shape_and_nonnegative() -> None:
    y = make_series(45)
    for forecaster in (ets_forecast, lightgbm_forecast):
        out = forecaster(y, 8)
        assert out.shape == (8, 3)
        assert np.isfinite(out).all()
        assert (out >= 0).all()


def test_lightgbm_is_deterministic() -> None:
    y = make_series(45)
    assert np.array_equal(lightgbm_forecast(y, 4, seed=1), lightgbm_forecast(y, 4, seed=1))


def test_ets_handles_all_zero_series() -> None:
    y = np.zeros((40, 2))
    assert (ets_forecast(y, 4) == 0).all()


def test_lightgbm_rejects_too_little_history() -> None:
    with pytest.raises(ValueError):
        lightgbm_forecast(np.ones((5, 2)), 4)


# ---------------------------------------------------------------- selection
def _bt_for_selection(candidate_wape: float) -> pd.DataFrame:
    """One category with actual = 100; naive is off by 20, the candidate by candidate_wape * 100."""
    rows = []
    for origin in (0, 1):
        for model, error in (
            ("naive", 20.0),
            ("moving_average_4", 25.0),
            ("ets", candidate_wape * 100),
        ):
            for h in (1, 2):
                rows.append(
                    {
                        "origin_idx": origin,
                        "origin_week": pd.Timestamp("2017-01-02"),
                        "category": "x",
                        "horizon": h,
                        "target_week": pd.Timestamp("2017-02-01"),
                        "actual": 100.0,
                        "model": model,
                        "forecast": 100.0 - error,
                    }
                )
    return pd.DataFrame(rows)


def test_selection_falls_back_to_baseline_when_candidate_is_not_clearly_better() -> None:
    bt = _bt_for_selection(candidate_wape=0.19)  # only 5% better than naive's 0.20 -> not enough
    choice = select_models(bt, [0, 1], candidates=("ets",), margin=0.10)
    assert choice.loc[0, "chosen_model"] == "naive"
    assert "baseline fallback" in choice.loc[0, "reason"]


def test_selection_picks_candidate_when_it_clearly_wins() -> None:
    bt = _bt_for_selection(candidate_wape=0.10)  # 50% better than naive
    choice = select_models(bt, [0, 1], candidates=("ets",), margin=0.05)
    assert choice.loc[0, "chosen_model"] == "ets"
    assert choice.loc[0, "improvement_pct"] == pytest.approx(50.0)


def test_selection_uses_only_selection_origins() -> None:
    bt = _bt_for_selection(candidate_wape=0.10)
    # Make the candidate terrible on origin 1 only; selecting on origin 0 alone must ignore that
    bt.loc[(bt["origin_idx"] == 1) & (bt["model"] == "ets"), "forecast"] = 0.0
    choice = select_models(bt, [0], candidates=("ets",), margin=0.05)
    assert choice.loc[0, "chosen_model"] == "ets"


def test_policy_rows_relabel_chosen_model() -> None:
    bt = _bt_for_selection(candidate_wape=0.10)
    choice = select_models(bt, [0, 1], candidates=("ets",), margin=0.05)
    policy = policy_rows(bt, choice)
    assert set(policy["model"]) == {SELECTED}
    assert len(policy) == len(bt[bt["model"] == "ets"])


# ---------------------------------------------------------------- error bands
def test_error_band_contains_point_forecast_and_has_sensible_coverage() -> None:
    rng = np.random.default_rng(3)
    forecast = rng.uniform(5, 50, 400)
    actual = forecast * rng.normal(1.0, 0.2, 400)
    policy = pd.DataFrame({"category": "x", "forecast": forecast, "actual": actual})
    q = residual_quantiles(policy, 0.10, 0.90)
    assert q.loc[0, "q_low"] < 0 < q.loc[0, "q_high"]
    assert 70 <= interval_coverage(policy, q) <= 90  # nominal 80%


# ---------------------------------------------------------------- data validation
def _panel(n_weeks: int = 6) -> pd.DataFrame:
    weeks = pd.date_range("2017-01-02", periods=n_weeks, freq="7D")
    rows = [
        {"week_start": w, "category": c, "units": 5, "category_revenue_rank": r}
        for r, c in enumerate(["a", "b"], start=1)
        for w in weeks
    ]
    return pd.DataFrame(rows)


def test_valid_panel_passes_and_converts() -> None:
    df = _panel()
    validate_panel(df)
    y, weeks, cats = to_matrix(df)
    assert y.shape == (6, 2) and len(weeks) == 6 and cats == ["a", "b"]


def test_validation_rejects_duplicates() -> None:
    df = pd.concat([_panel(), _panel().head(1)], ignore_index=True)
    with pytest.raises(ForecastDataError, match="duplicate"):
        validate_panel(df)


def test_validation_rejects_gaps() -> None:
    df = _panel()
    df = df[df["week_start"] != df["week_start"].iloc[2]]  # drop one week entirely
    with pytest.raises(ForecastDataError, match="not consecutive"):
        validate_panel(df)


def test_validation_rejects_negative_and_null_units() -> None:
    bad = _panel()
    bad.loc[0, "units"] = -1
    with pytest.raises(ForecastDataError, match="negative"):
        validate_panel(bad)
    null = _panel().astype({"units": float})
    null.loc[0, "units"] = np.nan
    with pytest.raises(ForecastDataError, match="null"):
        validate_panel(null)


def test_validation_rejects_non_monday_weeks() -> None:
    df = _panel()
    df["week_start"] = df["week_start"] + pd.Timedelta(days=1)
    with pytest.raises(ForecastDataError, match="Mondays"):
        validate_panel(df)


def test_validation_rejects_category_missing_a_week() -> None:
    df = _panel()
    df = df.drop(df[(df["category"] == "b")].index[0])
    with pytest.raises(ForecastDataError, match="missing weeks"):
        validate_panel(df)
