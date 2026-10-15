"""Tests for ingestion/load_raw.py using small synthetic CSVs (no real dataset needed)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ingestion.config import RAW_SCHEMA, TABLES, TableSpec
from ingestion.load_raw import (
    IngestionError,
    run_ingestion,
    validate_columns,
    validate_files,
)


def write_csv(path: Path, columns: tuple[str, ...], rows: list[list[str]]) -> None:
    """Write a simple CSV. Values are quoted so embedded commas/newlines are valid."""
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join('"' + value.replace('"', '""') + '"' for value in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """A directory with one valid data row for every expected table."""
    directory = tmp_path / "raw"
    directory.mkdir()
    for spec in TABLES:
        row = [f"{spec.name}_{col}_1" for col in spec.columns]
        write_csv(directory / spec.filename, spec.columns, [row])
    return directory


def test_happy_path_loads_all_tables(raw_dir: Path, tmp_path: Path) -> None:
    db_path = tmp_path / "wh.duckdb"
    counts = run_ingestion(raw_dir=raw_dir, db_path=db_path)

    assert set(counts) == {spec.name for spec in TABLES}
    assert all(n == 1 for n in counts.values())

    con = duckdb.connect(str(db_path))
    tables = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = ?", [RAW_SCHEMA]
        ).fetchall()
    }
    con.close()
    assert tables == {spec.name for spec in TABLES}


def test_metadata_columns_added(raw_dir: Path, tmp_path: Path) -> None:
    db_path = tmp_path / "wh.duckdb"
    run_ingestion(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    row = con.execute(f"SELECT _loaded_at, _source_file FROM {RAW_SCHEMA}.orders").fetchone()
    con.close()
    assert row is not None
    assert row[0] is not None
    assert row[1] == "olist_orders_dataset.csv"


def test_all_columns_loaded_as_varchar(raw_dir: Path, tmp_path: Path) -> None:
    """Bronze must not infer types (e.g. zip codes like 01046 keep their leading zero)."""
    spec = next(t for t in TABLES if t.name == "customers")
    write_csv(
        raw_dir / spec.filename,
        spec.columns,
        [["c1", "u1", "01046", "sao paulo", "SP"]],
    )
    db_path = tmp_path / "wh.duckdb"
    run_ingestion(raw_dir=raw_dir, db_path=db_path)

    con = duckdb.connect(str(db_path))
    value = con.execute(f"SELECT customer_zip_code_prefix FROM {RAW_SCHEMA}.customers").fetchone()
    types = {
        r[0]: r[1]
        for r in con.execute(f"DESCRIBE {RAW_SCHEMA}.customers").fetchall()
        if not r[0].startswith("_")
    }
    con.close()
    assert value is not None and value[0] == "01046"
    assert set(types.values()) == {"VARCHAR"}


def test_idempotent_rerun(raw_dir: Path, tmp_path: Path) -> None:
    db_path = tmp_path / "wh.duckdb"
    first = run_ingestion(raw_dir=raw_dir, db_path=db_path)
    second = run_ingestion(raw_dir=raw_dir, db_path=db_path)
    assert first == second  # no duplicated rows after re-running


def test_multiline_quoted_field(raw_dir: Path, tmp_path: Path) -> None:
    """Review comments contain newlines, commas and quotes; they must stay one row."""
    spec = next(t for t in TABLES if t.name == "order_reviews")
    write_csv(
        raw_dir / spec.filename,
        spec.columns,
        [["r1", "o1", "5", "", 'Great, "fast"\ndelivery', "2018-01-01", "2018-01-02"]],
    )
    db_path = tmp_path / "wh.duckdb"
    counts = run_ingestion(raw_dir=raw_dir, db_path=db_path)
    assert counts["order_reviews"] == 1


def test_missing_file_raises(raw_dir: Path, tmp_path: Path) -> None:
    (raw_dir / TABLES[0].filename).unlink()
    with pytest.raises(IngestionError, match="Missing 1 expected file"):
        run_ingestion(raw_dir=raw_dir, db_path=tmp_path / "wh.duckdb")


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="Raw data directory not found"):
        validate_files(tmp_path / "nope", TABLES)


def test_missing_column_raises(raw_dir: Path, tmp_path: Path) -> None:
    spec = next(t for t in TABLES if t.name == "orders")
    bad_cols = tuple(c for c in spec.columns if c != "order_status")
    write_csv(raw_dir / spec.filename, bad_cols, [[f"v_{c}" for c in bad_cols]])
    with pytest.raises(IngestionError, match="order_status"):
        run_ingestion(raw_dir=raw_dir, db_path=tmp_path / "wh.duckdb")


def test_empty_file_raises(raw_dir: Path) -> None:
    path = raw_dir / TABLES[0].filename
    path.write_text("", encoding="utf-8")
    with pytest.raises(IngestionError, match="empty"):
        validate_columns(path, TABLES[0].columns)


def test_header_only_file_raises(raw_dir: Path, tmp_path: Path) -> None:
    spec = TABLES[0]
    write_csv(raw_dir / spec.filename, spec.columns, [])
    with pytest.raises(IngestionError, match="0 rows"):
        run_ingestion(raw_dir=raw_dir, db_path=tmp_path / "wh.duckdb")


def test_bad_input_leaves_warehouse_untouched(raw_dir: Path, tmp_path: Path) -> None:
    """Validation happens before loading, so a bad file must not create a partial warehouse."""
    (raw_dir / TABLES[-1].filename).unlink()
    db_path = tmp_path / "wh.duckdb"
    with pytest.raises(IngestionError):
        run_ingestion(raw_dir=raw_dir, db_path=db_path)
    assert not db_path.exists()


def test_extra_column_only_warns(raw_dir: Path, tmp_path: Path) -> None:
    spec: TableSpec = TABLES[0]
    cols = (*spec.columns, "surprise_col")
    write_csv(raw_dir / spec.filename, cols, [[f"v_{c}" for c in cols]])
    counts = run_ingestion(raw_dir=raw_dir, db_path=tmp_path / "wh.duckdb")
    assert counts[spec.name] == 1
