"""Forecasting settings and shared names."""

from __future__ import annotations

from dataclasses import dataclass

# Model names used in every output table
NAIVE = "naive"
MOVING_AVERAGE = "moving_average_4"
SEASONAL_NAIVE = "seasonal_naive_52"
ETS = "ets"
LIGHTGBM = "lightgbm"
SELECTED = "selected"  # the per-category policy: best candidate, or a baseline fallback

BASELINE_MODELS = (NAIVE, MOVING_AVERAGE)  # always available, used as the fallback
CANDIDATE_MODELS = (ETS, LIGHTGBM)
MA_WINDOW = 4

OUTPUT_SCHEMA = "forecast"


@dataclass(frozen=True)
class ForecastConfig:
    """All tunable settings in one place (no magic numbers in the code)."""

    top_n: int = 15  # forecast the N largest categories by revenue
    horizon: int = 8  # weeks ahead
    min_train_weeks: int = 30  # shortest history a backtest origin may use
    # Drop this many of the NEWEST weeks before modelling. Default 0. Use 1 if the final week
    # is judged incomplete (see scripts/check_demand_tail.py).
    trim_last_weeks: int = 0
    origin_step: int = 4  # weeks between backtest origins
    selection_fraction: float = 0.6  # earliest share of origins used to pick models
    selection_margin: float = 0.05  # a model must beat the best baseline by this share
    # False (default): pick ONE candidate globally on pooled data, then let each category fall back
    # to a baseline. True: pick among all candidates per category (noisier with few origins).
    per_category_candidates: bool = False
    seed: int = 42
    interval_low: float = 0.10  # lower quantile of the empirical error band
    interval_high: float = 0.90  # upper quantile
    seasonal_period: int = 52
    # The Black-Friday period of the single holiday season in the data; used only to report
    # how each model copes with a demand spike.
    peak_start: str = "2017-11-20"
    peak_end: str = "2017-12-03"


DEFAULT_CONFIG = ForecastConfig()
