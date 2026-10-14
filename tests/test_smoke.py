"""Phase 1 smoke test: confirms the project skeleton and core imports work."""

from pathlib import Path

REQUIRED_DIRS = ["data/raw", "ingestion", "dbt_project", "forecasting", "dashboard", "tests", "docs"]


def test_core_imports() -> None:
    import duckdb  # noqa: F401
    import pandas  # noqa: F401


def test_folder_structure() -> None:
    root = Path(__file__).resolve().parent.parent
    missing = [d for d in REQUIRED_DIRS if not (root / d).is_dir()]
    assert not missing, f"Missing folders: {missing}"
