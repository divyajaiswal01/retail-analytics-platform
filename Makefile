.PHONY: setup ingest transform test-dbt forecast dashboard lint typecheck test run clean

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt
	pre-commit install

ingest:
	$(PYTHON) -m ingestion.load_raw

transform:
	cd dbt_project && dbt run

test-dbt:
	cd dbt_project && dbt test

forecast:
	$(PYTHON) -m forecasting.train

dashboard:
	streamlit run dashboard/app.py

lint:
	ruff check . && ruff format --check .

typecheck:
	mypy ingestion forecasting scripts dashboard

test:
	pytest

# Full pipeline (grows as phases are completed)
run: ingest transform test-dbt forecast

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dbt_project/target
