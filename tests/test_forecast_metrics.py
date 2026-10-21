"""Tests for forecasting/metrics.py."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from forecasting.metrics import bias, mae, summarize, wape


def test_wape_known_value() -> None:
    actual = np.array([10.0, 20.0, 30.0])
    forecast = np.array([12.0, 18.0, 33.0])
    # errors 2 + 2 + 3 = 7, total actual 60
    assert wape(actual, forecast) == pytest.approx(7 / 60)


def test_wape_perfect_forecast_is_zero() -> None:
    actual = np.array([5.0, 6.0, 7.0])
    assert wape(actual, actual) == 0.0


def test_wape_is_nan_when_no_actual_demand() -> None:
    assert math.isnan(wape(np.zeros(3), np.array([1.0, 1.0, 1.0])))


def test_bias_sign_over_and_under_forecasting() -> None:
    actual = np.array([10.0, 10.0])
    assert bias(actual, np.array([12.0, 12.0])) == pytest.approx(0.2)  # over-forecast
    assert bias(actual, np.array([8.0, 8.0])) == pytest.approx(-0.2)  # under-forecast


def test_mae_known_value() -> None:
    assert mae(np.array([1.0, 2.0, 3.0]), np.array([2.0, 2.0, 5.0])) == pytest.approx(1.0)


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="Shape mismatch"):
        wape(np.zeros(3), np.zeros(4))


def test_summarize_groups_correctly() -> None:
    df = pd.DataFrame(
        {
            "model": ["a", "a", "b", "b"],
            "actual": [10.0, 10.0, 10.0, 10.0],
            "forecast": [10.0, 10.0, 5.0, 15.0],
        }
    )
    out = summarize(df, ["model"]).set_index("model")
    assert out.loc["a", "wape"] == 0.0
    assert out.loc["b", "wape"] == pytest.approx(0.5)
    assert out.loc["b", "bias"] == pytest.approx(0.0)  # over and under cancel; WAPE does not
