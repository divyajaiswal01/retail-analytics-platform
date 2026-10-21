"""Statistical and machine-learning forecasters (same interface as the baselines)."""

from __future__ import annotations

import warnings

import numpy as np
import numpy.typing as npt
from lightgbm import LGBMRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from forecasting.baselines import moving_average
from ingestion.logger import get_logger

log = get_logger("forecasting.models")

Array = npt.NDArray[np.float64]

MIN_ETS_WEEKS = 10
LOOKBACK = 8  # weeks of history used to build features and the scale
MIN_TRAIN_ROWS = 10


def ets_forecast(history: Array, horizon: int) -> Array:
    """Damped-trend exponential smoothing, fitted per category.

    No seasonality is modelled: under two years of data is too little to learn a yearly cycle.
    If a series cannot be fitted, that category falls back to a moving average (warning logged).
    """
    n_weeks, n_cats = history.shape
    out = np.zeros((horizon, n_cats))
    for j in range(n_cats):
        y = history[:, j]
        fallback = moving_average(y.reshape(-1, 1), horizon)[:, 0]
        if n_weeks < MIN_ETS_WEEKS or not np.any(y > 0):
            out[:, j] = fallback
            continue
        try:
            with warnings.catch_warnings():
                # statsmodels emits convergence chatter on short, noisy series; failures are
                # caught below, so only the noise is silenced here.
                warnings.simplefilter("ignore")
                fit = ExponentialSmoothing(
                    y, trend="add", damped_trend=True, initialization_method="estimated"
                ).fit()
            forecast = np.asarray(fit.forecast(horizon), dtype=np.float64)
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            log.warning("ETS failed for category index %d (%s); using moving average", j, exc)
            out[:, j] = fallback
            continue
        if not np.isfinite(forecast).all():
            log.warning("ETS gave non-finite values for category index %d; using moving average", j)
            out[:, j] = fallback
            continue
        out[:, j] = np.clip(forecast, 0, None)
    return out


def _scale(history: Array, t: int) -> Array:
    """Mean of the last LOOKBACK weeks up to and including week ``t`` (plus 1 to avoid zero)."""
    return history[t - LOOKBACK + 1 : t + 1].mean(axis=0) + 1.0


def _features(history: Array, t: int) -> Array:
    """Scale-free features for every category at week ``t``, built only from weeks <= t."""
    scale = _scale(history, t)
    window = history[t - LOOKBACK + 1 : t + 1]
    n_cats = history.shape[1]
    columns = [history[t - k] / scale for k in range(4)]  # last four weeks, relative to level
    columns += [
        history[t - 3 : t + 1].mean(axis=0) / scale,
        window.std(axis=0) / scale,
        np.log(scale),
        np.arange(n_cats, dtype=np.float64),  # category index (categories are ordered by size)
    ]
    return np.column_stack(columns)


def lightgbm_forecast(history: Array, horizon: int, seed: int = 42) -> Array:
    """One global gradient-boosting model per horizon, trained across all categories.

    Targets and features are divided by each category's recent level, so large and small
    categories share one model. Training rows only use weeks whose target is already known.
    """
    n_weeks, n_cats = history.shape
    last = n_weeks - 1
    if last < LOOKBACK - 1:
        raise ValueError(f"Need at least {LOOKBACK} weeks of history, got {n_weeks}.")
    x_pred = _features(history, last)
    scale_pred = _scale(history, last)
    out = np.zeros((horizon, n_cats))

    for h in range(1, horizon + 1):
        times = range(LOOKBACK - 1, n_weeks - h)  # weeks t where week t+h is already observed
        if len(times) * n_cats < MIN_TRAIN_ROWS:
            raise ValueError(f"Not enough history to train a {h}-week-ahead model.")
        x = np.vstack([_features(history, t) for t in times])
        y = np.concatenate([history[t + h] / _scale(history, t) for t in times])
        model = LGBMRegressor(
            n_estimators=150,
            learning_rate=0.05,
            num_leaves=8,
            min_child_samples=15,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            random_state=seed,
            n_jobs=1,
            deterministic=True,
            force_row_wise=True,
            verbose=-1,
        )
        model.fit(x, y)
        out[h - 1] = np.clip(model.predict(x_pred) * scale_pred, 0, None)
    return out
