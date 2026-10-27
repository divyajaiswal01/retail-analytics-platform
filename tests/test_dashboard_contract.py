"""Contract test: every column the dashboard queries must exist in the data it reads.

- mart columns must be documented in the dbt schema files (so dbt tests and docs cover them)
- forecast columns must be produced by the real forecasting pipeline
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
import yaml

from dashboard.components import queries
from forecasting.config import DEFAULT_CONFIG
from forecasting.train import run

ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = ROOT / "dbt_project" / "models" / "marts"

QUERY_FUNCTIONS = [
    queries.summary,
    queries.monthly_kpis,
    queries.categories,
    queries.states,
    queries.delivery_impact,
    queries.delivery_vs_repeat,
    queries.sellers,
    queries.sales_cube,
    queries.weekly_demand,
    queries.forecast_run,
    queries.forecast,
    queries.forecast_all_models,
    queries.accuracy_summary,
    queries.horizon_accuracy,
    queries.uncertainty,
]


def captured_sql(function) -> str:  # type: ignore[no-untyped-def]
    """Run a query function with ``load`` replaced by a recorder and return the SQL it sends."""
    seen: list[str] = []

    def fake_load(sql: str, params=()):  # type: ignore[no-untyped-def]
        seen.append(sql)
        return pd.DataFrame()

    original = queries.load
    queries.load = fake_load  # type: ignore[assignment]
    try:
        function()
    finally:
        queries.load = original  # type: ignore[assignment]
    return seen[0]


def parse(sql: str) -> tuple[str, str, list[str]]:
    """Return (schema, table, selected columns) for a simple SELECT ... FROM schema.table."""
    match = re.search(r"SELECT\s+(.*?)\s+FROM\s+(\w+)\.(\w+)", sql, re.DOTALL | re.IGNORECASE)
    assert match, f"Could not parse: {sql}"
    columns = [c.strip() for c in match.group(1).split(",")]
    return match.group(2), match.group(3), columns


def documented_columns() -> dict[str, set[str]]:
    """Model name -> column names documented in the dbt schema files."""
    out: dict[str, set[str]] = {}
    for path in MARTS_DIR.glob("*.yml"):
        for model in yaml.safe_load(path.read_text()).get("models", []):
            out.setdefault(model["name"], set()).update(c["name"] for c in model.get("columns", []))
    return out


@pytest.fixture(scope="module")
def forecast_columns(tmp_path_factory: pytest.TempPathFactory) -> dict[str, set[str]]:
    """Columns of the tables the real forecasting pipeline writes (tiny synthetic warehouse)."""
    path = tmp_path_factory.mktemp("contract") / "wh.duckdb"
    rng = np.random.default_rng(5)
    weeks = pd.date_range("2017-01-02", periods=60, freq="7D")
    rows = [
        {
            "demand_key": f"{c}|{w.date()}",
            "week_start": w.date(),
            "category": c,
            "units": int(rng.poisson(20 - 6 * r)),
            "orders": 1,
            "revenue": 1.0,
            "category_revenue_rank": r,
        }
        for r, c in enumerate(["a", "b", "c"], start=1)
        for w in weeks
    ]
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA marts")
    frame = pd.DataFrame(rows)
    con.register("f", frame)
    con.execute("CREATE TABLE marts.mart_weekly_category_demand AS SELECT * FROM f")
    con.close()
    config = replace(DEFAULT_CONFIG, top_n=3, horizon=4, min_train_weeks=26, origin_step=4)
    tables = run(db_path=path, config=config, use_mlflow=False)
    return {name: set(frame.columns) for name, frame in tables.items()}


@pytest.mark.parametrize("function", QUERY_FUNCTIONS, ids=lambda f: f.__name__)
def test_every_queried_column_exists(function, forecast_columns) -> None:  # type: ignore[no-untyped-def]
    schema, table, columns = parse(captured_sql(function))
    if schema == "marts":
        documented = documented_columns()
        assert table in documented, f"marts.{table} has no dbt schema entry"
        missing = [c for c in columns if c not in documented[table]]
        assert not missing, f"marts.{table}: dashboard reads undocumented column(s) {missing}"
    elif schema == "forecast":
        assert table in forecast_columns, f"forecast.{table} is not written by the pipeline"
        missing = [c for c in columns if c not in forecast_columns[table]]
        assert not missing, f"forecast.{table}: dashboard reads missing column(s) {missing}"
    else:
        pytest.fail(f"Dashboard must only read marts or forecast tables, got {schema}.{table}")


def test_dashboard_never_reads_raw_or_staging_tables() -> None:
    for function in QUERY_FUNCTIONS:
        schema, _, _ = parse(captured_sql(function))
        assert schema in {"marts", "forecast"}
