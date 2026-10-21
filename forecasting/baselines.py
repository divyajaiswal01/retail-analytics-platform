"""Baseline forecasters.

Each takes ``history`` (weeks x categories) and returns (horizon x categories).
A forecaster only ever sees the history it is given, so it cannot use future data.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from forecasting.config import MA_WINDOW

Array = npt.NDArray[np.float64]


def naive(history: Array, horizon: int) -> Array:
    """Repeat the most recent week."""
    return np.tile(history[-1], (horizon, 1))


def moving_average(history: Array, horizon: int, window: int = MA_WINDOW) -> Array:
    """Repeat the mean of the last ``window`` weeks."""
    return np.tile(history[-window:].mean(axis=0), (horizon, 1))


def seasonal_naive(history: Array, horizon: int, period: int = 52) -> Array:
    """Use the value from the same week one year earlier (NaN until a year of history exists)."""
    n_weeks, n_cats = history.shape
    if n_weeks < period:
        return np.full((horizon, n_cats), np.nan)
    rows = [history[n_weeks - period + (h % period)] for h in range(horizon)]
    return np.vstack(rows)
