"""Forecast accuracy metrics."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd

Array = npt.NDArray[np.float64]


def _check(actual: Array, forecast: Array) -> tuple[Array, Array]:
    a = np.asarray(actual, dtype=np.float64)
    f = np.asarray(forecast, dtype=np.float64)
    if a.shape != f.shape:
        raise ValueError(f"Shape mismatch: actual {a.shape} vs forecast {f.shape}")
    return a, f


def wape(actual: Array, forecast: Array) -> float:
    """Weighted absolute percentage error: sum|a - f| / sum(a). NaN when sum(a) is zero."""
    a, f = _check(actual, forecast)
    total = float(a.sum())
    return float(np.abs(a - f).sum() / total) if total > 0 else float("nan")


def bias(actual: Array, forecast: Array) -> float:
    """Signed error: sum(f - a) / sum(a). Positive means over-forecasting."""
    a, f = _check(actual, forecast)
    total = float(a.sum())
    return float((f - a).sum() / total) if total > 0 else float("nan")


def mae(actual: Array, forecast: Array) -> float:
    """Mean absolute error in units."""
    a, f = _check(actual, forecast)
    return float(np.abs(a - f).mean())


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """WAPE, bias and MAE per group for a frame with ``actual`` and ``forecast`` columns."""
    rows = []
    for key, g in df.groupby(by, sort=False):
        a = g["actual"].to_numpy(dtype=np.float64)
        f = g["forecast"].to_numpy(dtype=np.float64)
        keys = key if isinstance(key, tuple) else (key,)
        rows.append(
            {
                **dict(zip(by, keys, strict=True)),
                "rows": len(g),
                "actual_units": float(a.sum()),
                "wape": wape(a, f),
                "bias": bias(a, f),
                "mae": mae(a, f),
            }
        )
    return pd.DataFrame(rows)
