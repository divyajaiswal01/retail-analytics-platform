"""Figure builders. Each takes DataFrames from the marts or forecast tables and only draws them."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COMPLETE = "#1f77b4"
INCOMPLETE = "#b0b0b0"


def _split_by_completeness(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    flag = df["is_complete_month"].astype(bool)
    return df[flag], df[~flag]


def monthly_bars(df: pd.DataFrame, value_col: str, title: str, y_title: str) -> go.Figure:
    """Monthly bars; incomplete months are grey so they are not mistaken for a decline."""
    complete, incomplete = _split_by_completeness(df)
    fig = go.Figure()
    fig.add_bar(
        x=complete["year_month"], y=complete[value_col], name="complete", marker_color=COMPLETE
    )
    if not incomplete.empty:
        fig.add_bar(
            x=incomplete["year_month"],
            y=incomplete[value_col],
            name="incomplete (understated)",
            marker_color=INCOMPLETE,
        )
    fig.update_layout(
        title=title, yaxis_title=y_title, xaxis_title=None, barmode="group", height=380
    )
    return fig


def monthly_line(df: pd.DataFrame, value_col: str, title: str, y_title: str) -> go.Figure:
    """Monthly line; incomplete months are drawn as grey diamonds."""
    complete, incomplete = _split_by_completeness(df)
    fig = go.Figure()
    fig.add_scatter(
        x=df["year_month"],
        y=df[value_col],
        mode="lines",
        line={"color": COMPLETE},
        showlegend=False,
    )
    fig.add_scatter(
        x=complete["year_month"],
        y=complete[value_col],
        mode="markers",
        name="complete",
        marker={"color": COMPLETE},
    )
    if not incomplete.empty:
        fig.add_scatter(
            x=incomplete["year_month"],
            y=incomplete[value_col],
            mode="markers",
            name="incomplete (understated)",
            marker={"color": INCOMPLETE, "size": 11, "symbol": "diamond"},
        )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title=None, height=380)
    return fig


def customers_new_vs_returning(df: pd.DataFrame) -> go.Figure:
    long = df.melt(
        id_vars="year_month",
        value_vars=["new_customers", "returning_customers"],
        var_name="type",
        value_name="customers",
    )
    long["type"] = long["type"].map({"new_customers": "new", "returning_customers": "returning"})
    fig = px.bar(long, x="year_month", y="customers", color="type", title="Customers per month")
    fig.update_layout(xaxis_title=None, yaxis_title="customers", height=380)
    return fig


def top_categories(df: pd.DataFrame) -> go.Figure:
    ordered = df.sort_values("revenue")
    fig = px.bar(
        ordered,
        x="revenue",
        y="category",
        orientation="h",
        title="Top categories by revenue (BRL)",
        hover_data={"revenue_share_pct": ":.2f", "cumulative_share_pct": ":.1f"},
    )
    fig.update_layout(yaxis_title=None, xaxis_title="revenue (BRL)", height=420)
    return fig


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str, x_title: str) -> go.Figure:
    ordered = df.sort_values(x)
    fig = px.bar(ordered, x=x, y=y, orientation="h", title=title)
    fig.update_layout(
        yaxis_title=None, xaxis_title=x_title, height=max(320, 26 * len(ordered) + 120)
    )
    return fig


def review_by_bucket(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("bucket_order"),
        x="delivery_bucket",
        y="avg_review_score",
        text="avg_review_score",
        title="Average review score by delivery lateness",
        hover_data={"orders": ":,", "pct_low_reviews": ":.1f", "pct_five_star": ":.1f"},
    )
    fig.update_traces(texttemplate="%{text:.2f}")
    fig.update_layout(
        xaxis_title=None, yaxis_title="average review score (1-5)", yaxis_range=[0, 5], height=380
    )
    return fig


def category_heatmap(pivot: pd.DataFrame) -> go.Figure:
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        title="Revenue by category and state (BRL)",
    )
    fig.update_layout(height=max(360, 28 * len(pivot) + 140), coloraxis_colorbar={"title": "BRL"})
    return fig


def forecast_chart(
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    baselines: pd.DataFrame,
    category: str,
    chosen_model: str,
) -> go.Figure:
    """History, the chosen forecast with its error band, and the baselines for comparison."""
    fig = go.Figure()
    fig.add_scatter(
        x=history["week_start"],
        y=history["units"],
        name="actual",
        mode="lines",
        line={"color": COMPLETE},
    )
    if not forecast.empty:
        fig.add_scatter(
            x=forecast["week_start"],
            y=forecast["upper_units"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
        fig.add_scatter(
            x=forecast["week_start"],
            y=forecast["lower_units"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(255,127,14,0.2)",
            name="error band (approx.)",
            hoverinfo="skip",
        )
        fig.add_scatter(
            x=forecast["week_start"],
            y=forecast["forecast_units"],
            mode="lines+markers",
            name=f"forecast ({chosen_model})",
            line={"color": "#ff7f0e"},
        )
    dashes = {"moving_average_4": "dot", "naive": "dash"}
    for model, group in baselines.groupby("model"):
        if model in dashes:
            fig.add_scatter(
                x=group["week_start"],
                y=group["forecast_units"],
                mode="lines",
                name=str(model),
                line={"dash": dashes[str(model)], "color": "#7f7f7f"},
            )
    fig.update_layout(
        title=f"{category}: weekly units and 8-week forecast",
        yaxis_title="units per week",
        xaxis_title=None,
        height=430,
    )
    return fig


def total_outlook(
    history_total: pd.DataFrame, forecast_total: pd.DataFrame, baseline_total: pd.DataFrame
) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=history_total["week_start"],
        y=history_total["units"],
        name="actual",
        mode="lines",
        line={"color": COMPLETE},
    )
    fig.add_scatter(
        x=forecast_total["week_start"],
        y=forecast_total["forecast_units"],
        name="forecast (chosen models)",
        mode="lines+markers",
        line={"color": "#ff7f0e"},
    )
    fig.add_scatter(
        x=baseline_total["week_start"],
        y=baseline_total["forecast_units"],
        name="moving_average_4",
        mode="lines",
        line={"dash": "dot", "color": "#7f7f7f"},
    )
    fig.update_layout(
        title="All forecast categories: weekly units",
        yaxis_title="units per week",
        xaxis_title=None,
        height=400,
    )
    return fig


def accuracy_bars(df: pd.DataFrame, title: str) -> go.Figure:
    ordered = df.sort_values("wape")
    fig = px.bar(ordered, x="model", y="wape", text="wape", title=title)
    fig.update_traces(texttemplate="%{text:.3f}")
    fig.update_layout(xaxis_title=None, yaxis_title="WAPE (lower is better)", height=380)
    return fig


def horizon_lines(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df.sort_values("horizon"),
        x="horizon",
        y="wape",
        color="model",
        markers=True,
        title="Holdout WAPE by weeks ahead",
    )
    fig.update_layout(xaxis_title="weeks ahead", yaxis_title="WAPE", height=380)
    return fig


def uncertainty_bars(df: pd.DataFrame) -> go.Figure:
    ordered = df.sort_values("holdout_wape")
    fig = px.bar(
        ordered,
        x="holdout_wape",
        y="category",
        color="chosen_model",
        orientation="h",
        title="Holdout WAPE by category (higher = harder to forecast)",
    )
    fig.update_layout(
        yaxis_title=None, xaxis_title="WAPE", height=max(360, 28 * len(ordered) + 120)
    )
    return fig
