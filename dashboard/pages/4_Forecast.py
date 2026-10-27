"""Forecast: 8-week category demand forecasts, accuracy and uncertainty."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # dashboard/pages/<file> -> project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components import charts, queries  # noqa: E402
from dashboard.components.data import DashboardDataError  # noqa: E402
from dashboard.components.definitions import DEFINITIONS  # noqa: E402
from dashboard.components.ui import (  # noqa: E402
    date_str,
    num,
    pct,
    show_chart,
    show_error,
    show_table,
)

st.title("Weekly Demand Forecast")

try:
    with st.spinner("Loading data..."):
        run_df = queries.forecast_run()
        history = queries.weekly_demand()
        forecast = queries.forecast()
        all_models = queries.forecast_all_models()
        accuracy = queries.accuracy_summary()
        horizon = queries.horizon_accuracy()
        uncertainty = queries.uncertainty()
except DashboardDataError as exc:
    show_error(exc)
    st.stop()

if run_df.empty or forecast.empty or uncertainty.empty:
    st.warning("The forecast tables are empty. Run `python -m forecasting.train`.")
    st.stop()

run = run_df.iloc[0]
first_forecast_week = forecast["week_start"].min()
st.info(
    f"Forecast generated {run['run_at_utc']} UTC from weekly history through "
    f"{date_str(run['last_week'])}. "
    f"It covers the {int(run['categories'])} largest categories and starts the week of "
    f"{date_str(first_forecast_week)}. Later weeks cannot be checked against real data."
)

categories = uncertainty.sort_values("revenue_rank")["category"].tolist()
history = history[history["category"].isin(categories)]

tab_cat, tab_total, tab_acc, tab_unc = st.tabs(
    ["Category forecast", "Total outlook", "Accuracy", "Uncertainty"]
)

with tab_cat:
    left, right = st.columns([2, 1])
    category = left.selectbox("Category", categories)
    span = (
        right.selectbox("History shown", ["Last 26 weeks", "Last 52 weeks", "All history"], index=1)
        or "Last 52 weeks"
    )
    hist_cat = history[history["category"] == category].sort_values("week_start")
    if span.startswith("Last"):
        hist_cat = hist_cat.tail(int(span.split()[1]))
    info = uncertainty[uncertainty["category"] == category].iloc[0]
    fc_cat = forecast[forecast["category"] == category]
    base_cat = all_models[all_models["category"] == category]
    show_chart(
        charts.forecast_chart(hist_cat, fc_cat, base_cat, category, str(info["chosen_model"])),
        key="fc_cat",
    )

    recent_avg = (
        history[history["category"] == category].sort_values("week_start")["units"].tail(4).mean()
    )
    forecast_avg = fc_cat["forecast_units"].mean()
    cols = st.columns(3)
    cols[0].metric("Model used", str(info["chosen_model"]))
    cols[1].metric(
        "Holdout error (WAPE)", pct(100 * info["holdout_wape"], 1), help=DEFINITIONS["wape"]
    )
    delta = (
        f"{100 * (forecast_avg / recent_avg - 1):+.1f}% vs last 4 weeks" if recent_avg > 0 else None
    )
    cols[2].metric("Avg weekly forecast", num(forecast_avg), delta=delta)
    st.caption(
        "Orange band: approximate error range from past forecast errors (see the Uncertainty tab). "
        "Grey lines are simple baselines for comparison."
    )

with tab_total:
    hist_total = history.groupby("week_start")["units"].sum().reset_index()
    fc_total = forecast.groupby("week_start")["forecast_units"].sum().reset_index()
    ma_total = (
        all_models[all_models["model"] == "moving_average_4"]
        .groupby("week_start")["forecast_units"]
        .sum()
        .reset_index()
    )
    show_chart(charts.total_outlook(hist_total.tail(52), fc_total, ma_total), key="fc_total")
    recent = hist_total.sort_values("week_start")["units"].tail(4).mean()
    cols = st.columns(3)
    cols[0].metric("Avg weekly forecast", num(fc_total["forecast_units"].mean()))
    cols[1].metric("Last 4 weeks, avg weekly", num(recent))
    cols[2].metric("Change", f"{100 * (fc_total['forecast_units'].mean() / recent - 1):+.1f}%")
    st.caption(
        "No error band is shown for the total: adding up the category bands would overstate the "
        "uncertainty, because errors in different categories partly cancel. The forecast is a "
        "statistical extrapolation of recent demand with no knowledge of promotions or events."
    )

with tab_acc:
    scopes = {
        "holdout_origins": "Holdout (latest forecast origins, the honest test)",
        "all_origins": "All backtest origins",
        "full_year_origins": "Origins with a full year of history (fair for seasonal naive)",
        "peak_weeks": "Black Friday weeks only",
    }
    available = [s for s in scopes if s in set(accuracy["scope"])]
    scope = st.selectbox("Evaluation set", available, format_func=lambda s: scopes[s])
    chosen = accuracy[accuracy["scope"] == scope]
    show_chart(charts.accuracy_bars(chosen, "WAPE by model (lower is better)"), key="acc")
    show_table(
        chosen.sort_values("wape")[["model", "rows", "wape", "bias", "mae"]],
        formats={"wape": "%.3f", "bias": "%.3f", "mae": "%.1f"},
    )
    st.caption(
        f"WAPE: {DEFINITIONS['wape']} Bias: {DEFINITIONS['bias']} The holdout uses only "
        f"{int(run['holdout_origins'])} forecast origins with overlapping targets, so small "
        "differences between models are within noise."
    )
    show_chart(charts.horizon_lines(horizon), key="horizon")
    st.caption("Holdout error by how many weeks ahead the forecast looks.")

with tab_unc:
    cols = st.columns(2)
    cols[0].metric(
        "Error band coverage on holdout",
        pct(run["holdout_interval_coverage_pct"]),
        help="Share of actual weekly values that fell inside the band. The target is about 80%.",
    )
    cols[1].metric("Categories", int(run["categories"]))
    show_chart(charts.uncertainty_bars(uncertainty), key="unc")
    show_table(
        uncertainty[
            [
                "uncertainty_rank",
                "category",
                "chosen_model",
                "holdout_wape",
                "holdout_bias",
                "forecast_units",
            ]
        ],
        formats={"holdout_wape": "%.3f", "holdout_bias": "%.3f", "forecast_units": "%.0f"},
    )
    st.caption(
        "Categories are ranked from hardest to easiest to forecast (holdout WAPE). Plan more "
        "safety "
        "stock for the hardest ones. Bands are approximate and, in testing, captured slightly less "
        "than their nominal share of outcomes."
    )
