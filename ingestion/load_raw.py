"""Load the source CSV files into the DuckDB ``raw`` schema (bronze layer).

Design rules (see rules.md):
- Bronze is untouched: every column is loaded as VARCHAR; typing happens in dbt staging.
- Two metadata columns are added: ``_loaded_at`` and ``_source_file``.
- Validate EVERYTHING before loading ANYTHING, so a bad input never leaves a half-loaded warehouse.
- Idempotent: re-running replaces each table, giving identical results.
- Fail loudly: any problem raises ``IngestionError`` and the CLI exits non-zero.

Run with:  python -m ingestion.load_raw      (or: make ingest)
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from ingestion.config import RAW_SCHEMA, TABLES, TableSpec, get_raw_dir, get_warehouse_path
from ingestion.logger import get_logger

log = get_logger("ingestion")


class IngestionError(Exception):
    """Raised when source data is missing, malformed, or fails to load."""


def validate_files(raw_dir: Path, tables: tuple[TableSpec, ...]) -> None:
    """Ensure the raw directory and every expected CSV exist."""
    if not raw_dir.is_dir():
        raise IngestionError(
            f"Raw data directory not found: {raw_dir}. "
            "Check RAW_DATA_DIR in .env and that the dataset was downloaded."
        )
    missing = [t.filename for t in tables if not (raw_dir / t.filename).is_file()]
    if missing:
        raise IngestionError(
            f"Missing {len(missing)} expected file(s) in {raw_dir}: {', '.join(missing)}. "
            "Re-download the dataset or check the file names."
        )


def validate_columns(path: Path, expected: tuple[str, ...]) -> None:
    """Ensure the CSV header contains every expected column. Extra columns only warn."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), None)
    if not header:
        raise IngestionError(f"{path.name} is empty or has no header row.")

    header_set = {col.strip() for col in header}
    missing = [col for col in expected if col not in header_set]
    if missing:
        raise IngestionError(
            f"{path.name} is missing expected column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(header)}."
        )
    extra = sorted(header_set - set(expected))
    if extra:
        log.warning("%s has unexpected extra column(s): %s", path.name, ", ".join(extra))


def load_table(
    con: duckdb.DuckDBPyConnection, spec: TableSpec, raw_dir: Path, loaded_at: str
) -> int:
    """Load one CSV into ``raw.<name>`` (replacing any existing table). Returns the row count."""
    path = raw_dir / spec.filename
    started = time.perf_counter()
    target = f"{RAW_SCHEMA}.{spec.name}"  # trusted: comes from config, not user input
    try:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {target} AS
            SELECT
                *,
                CAST(? AS TIMESTAMP) AS _loaded_at,
                ? AS _source_file
            FROM read_csv(?, header = true, all_varchar = true)
            """,
            [loaded_at, spec.filename, str(path)],
        )
        result = con.execute(f"SELECT COUNT(*) FROM {target}").fetchone()
    except duckdb.Error as exc:
        raise IngestionError(f"Failed to load {spec.filename} into {target}: {exc}") from exc

    row_count = int(result[0]) if result else 0
    if row_count == 0:
        raise IngestionError(f"{spec.filename} loaded 0 rows into {target}; the file has no data.")

    log.info(
        "Loaded %-22s rows=%-9s file=%s (%.2fs)",
        target,
        f"{row_count:,}",
        spec.filename,
        time.perf_counter() - started,
    )
    return row_count


def run_ingestion(
    raw_dir: Path | None = None,
    db_path: Path | None = None,
    tables: tuple[TableSpec, ...] = TABLES,
) -> dict[str, int]:
    """Validate then load all tables. Returns ``{table_name: row_count}``."""
    raw_dir = raw_dir or get_raw_dir()
    db_path = db_path or get_warehouse_path()
    run_started = time.perf_counter()

    log.info("Starting ingestion | raw_dir=%s | warehouse=%s", raw_dir, db_path)

    # 1) Validate everything first: no partial loads from bad input.
    validate_files(raw_dir, tables)
    for spec in tables:
        validate_columns(raw_dir / spec.filename, spec.columns)
    log.info("Validation passed for %d files", len(tables))

    # 2) Load.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    counts: dict[str, int] = {}
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
        for spec in tables:
            counts[spec.name] = load_table(con, spec, raw_dir, loaded_at)
    finally:
        con.close()

    log.info(
        "Ingestion complete | tables=%d | total_rows=%s | %.2fs",
        len(counts),
        f"{sum(counts.values()):,}",
        time.perf_counter() - run_started,
    )
    return counts


def main() -> int:
    """CLI entry point. Returns a process exit code (0 = success)."""
    try:
        run_ingestion()
    except IngestionError as exc:
        log.error("Ingestion failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
