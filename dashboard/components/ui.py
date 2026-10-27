"""Display helpers: number formats, width handling that works across Streamlit versions."""

from __future__ import annotations

import inspect
from collections.abc import Mapping

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.data import DashboardDataError


def _is_missing(value: object) -> bool:
    return value is None or bool(pd.isna(value))  # type: ignore[call-overload]


def money(value: object) -> str:
    """BRL with thousands separators, e.g. R$ 13,181,027."""
    return "n/a" if _is_missing(value) else f"R$ {float(value):,.0f}"  # type: ignore[arg-type]


def money_short(value: object) -> str:
    """Compact BRL for KPI cards, e.g. R$ 13.18M."""
    if _is_missing(value):
        return "n/a"
    v = float(value)  # type: ignore[arg-type]
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"R$ {v / 1_000:,.1f}K"
    return f"R$ {v:,.0f}"


def date_str(value: object) -> str:
    """A date or timestamp as YYYY-MM-DD."""
    return "n/a" if _is_missing(value) else str(pd.Timestamp(value).date())  # type: ignore[arg-type]


def num(value: object, digits: int = 0) -> str:
    return "n/a" if _is_missing(value) else f"{float(value):,.{digits}f}"  # type: ignore[arg-type]


def pct(value: object, digits: int = 1) -> str:
    """Format a value that is already a percentage (e.g. 91.87 -> 91.9%)."""
    return "n/a" if _is_missing(value) else f"{float(value):,.{digits}f}%"  # type: ignore[arg-type]


def _width_kwargs(function: object) -> dict[str, object]:
    """Use the current ``width='stretch'`` argument where it exists, else the older flag."""
    params = inspect.signature(function).parameters  # type: ignore[arg-type]
    if "width" in params:
        return {"width": "stretch"}
    return {"use_container_width": True}


def show_chart(fig: go.Figure, key: str | None = None) -> None:
    """Render a Plotly figure at full width."""
    st.plotly_chart(fig, key=key, **_width_kwargs(st.plotly_chart))  # type: ignore[call-overload]


def show_table(
    df: pd.DataFrame, formats: Mapping[str, str] | None = None, height: int | None = None
) -> None:
    """Render a table without the index; ``formats`` maps column -> printf format."""
    config = {
        col: st.column_config.NumberColumn(format=fmt) for col, fmt in (formats or {}).items()
    }
    kwargs: dict[str, object] = {"hide_index": True, "column_config": config}
    if height:
        kwargs["height"] = height
    st.dataframe(df, **kwargs, **_width_kwargs(st.dataframe))  # type: ignore[call-overload]


def show_error(exc: DashboardDataError) -> None:
    """Show a data problem as a short message, never a stack trace."""
    st.error(str(exc))
    st.caption("Setup steps are in the README.")


def incomplete_months(df: pd.DataFrame, month_col: str = "year_month") -> list[str]:
    """Months flagged by dbt as incomplete (``is_complete_month`` is false)."""
    if "is_complete_month" not in df.columns:
        return []
    flagged = df.loc[~df["is_complete_month"].astype(bool), month_col]
    return sorted(set(flagged.astype(str)))
