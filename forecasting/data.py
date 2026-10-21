"""Load and validate the weekly demand panel from the warehouse."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import numpy.typing as npt
import pandas as pd

from ingestion.config import get_warehouse_path

REQUIRED_COLUMNS = ("week_start", "category", "units", "category_revenue_rank")


class ForecastDataError(Exception):
    """Raised when the demand data is missing or malformed."""


def load_weekly_demand(db_path: Path | None = None, top_n: int = 15) -> pd.DataFrame:
    """Read weekly units for the ``top_n`` categories by revenue (read-only)."""
    path = db_path or get_warehouse_path()
    if not path.exists():
        raise ForecastDataError(
            f"Warehouse not found: {path}. Run ingestion and `dbt build` first."
        )
    try:
        con = duckdb.connect(str(path), read_only=True)
    except duckdb.Error as exc:
        raise ForecastDataError(
            f"Cannot open {path}: {exc}. Close Jupyter or any other DuckDB session and retry."
        ) from exc
    try:
        df = con.execute(
            """
            SELECT week_start, category, units, category_revenue_rank
            FROM marts.mart_weekly_category_demand
            WHERE category_revenue_rank <= ?
            ORDER BY category_revenue_rank, week_start
            """,
            [top_n],
        ).df()
    except duckdb.CatalogException as exc:
        raise ForecastDataError(
            "Table marts.mart_weekly_category_demand not found. Run `dbt build` first."
        ) from exc
    finally:
        con.close()
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def validate_panel(df: pd.DataFrame) -> None:
    """Fail loudly unless the panel is complete: no gaps, duplicates, nulls or negatives."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ForecastDataError(f"Demand data is missing column(s): {', '.join(missing)}")
    if df.empty:
        raise ForecastDataError("Demand data is empty.")
    if df["units"].isna().any():
        raise ForecastDataError("Demand data contains null units.")
    if (df["units"] < 0).any():
        raise ForecastDataError("Demand data contains negative units.")

    duplicates = int(df.duplicated(["category", "week_start"]).sum())
    if duplicates:
        raise ForecastDataError(f"Demand data has {duplicates} duplicate category-week row(s).")

    weeks = pd.DatetimeIndex(sorted(df["week_start"].unique()))
    if (weeks.weekday != 0).any():
        raise ForecastDataError("Some week_start values are not Mondays.")
    if len(weeks) > 1 and not (weeks[1:] - weeks[:-1] == pd.Timedelta(days=7)).all():
        raise ForecastDataError("Weeks are not consecutive: there is a gap in the calendar.")

    per_category = df.groupby("category")["week_start"].nunique()
    short = per_category[per_category != len(weeks)]
    if not short.empty:
        raise ForecastDataError(
            f"{len(short)} categor(ies) are missing weeks, e.g. {short.index[0]!r}."
        )


def to_matrix(df: pd.DataFrame) -> tuple[npt.NDArray[np.float64], pd.DatetimeIndex, list[str]]:
    """Return ``(Y, weeks, categories)`` where ``Y`` has shape (weeks, categories)."""
    categories = (
        df.sort_values("category_revenue_rank").drop_duplicates("category")["category"].tolist()
    )
    pivot = df.pivot(index="week_start", columns="category", values="units").sort_index()
    pivot = pivot[categories]
    return pivot.to_numpy(dtype=np.float64), pd.DatetimeIndex(pivot.index), categories
