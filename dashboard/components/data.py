"""Read-only warehouse access for the dashboard.

Results are cached and refreshed automatically whenever the warehouse file changes (for example
after `dbt build` or `python -m forecasting.train`). Every failure is turned into a short,
readable ``DashboardDataError``: the app never shows a raw stack trace.
"""

from __future__ import annotations

from collections.abc import Sequence

import duckdb
import pandas as pd
import streamlit as st

from ingestion.config import get_warehouse_path


class DashboardDataError(Exception):
    """A problem with the data that the user can act on (message is safe to display)."""


@st.cache_data(show_spinner=False, ttl=3600)
def _run(sql: str, params: tuple[object, ...], path: str, version: float) -> pd.DataFrame:
    """Run one read-only query. ``path`` and ``version`` only serve as cache keys."""
    try:
        con = duckdb.connect(path, read_only=True)
    except duckdb.Error as exc:
        raise DashboardDataError(
            "The warehouse could not be opened. Close Jupyter or any other program using "
            "it (for example a running `dbt build`), then refresh this page."
        ) from exc
    try:
        return con.execute(sql, list(params)).df()
    except duckdb.CatalogException as exc:
        raise DashboardDataError(
            "A table this page needs is missing from the warehouse. Run the pipeline: "
            "`dbt build`, then `python -m forecasting.train`."
        ) from exc
    except duckdb.Error as exc:
        raise DashboardDataError(
            "The warehouse could not be queried. Re-run `dbt build` and try again."
        ) from exc
    finally:
        con.close()


def load(sql: str, params: Sequence[object] = ()) -> pd.DataFrame:
    """Return the query result as a DataFrame (cached, read-only)."""
    path = get_warehouse_path()
    if not path.exists():
        raise DashboardDataError(
            f"Warehouse not found at {path}. Run ingestion, then `dbt build`, "
            "then `python -m forecasting.train`."
        )
    return _run(sql, tuple(params), str(path), path.stat().st_mtime)
