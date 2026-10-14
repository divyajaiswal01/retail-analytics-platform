# Phases: Retail Analytics & Demand Forecasting Platform

Each phase has a goal, tasks, deliverables, and an exit criterion. Do not start the next phase until the current one's exit criterion is met. Suggested pace: about one phase per 3-5 days at part-time effort.

---

## Phase 1: Foundation & Business Framing
**Goal:** Lock the scope and set up a clean project skeleton.

**Tasks**
- [ ] Create the GitHub repo, `.gitignore`, and virtual environment
- [ ] Add `PRD.md`, `architecture.md`, `rules.md`, `phases.md`
- [ ] Install pinned dependencies; create `requirements.txt`
- [ ] Set up `ruff`, `mypy`, `pytest`, and `pre-commit`
- [ ] Create the folder structure from `architecture.md`
- [ ] Write `docs/business_case.md` (stakeholders, questions, KPIs)
- [ ] Download the Olist dataset into `data/raw/`

**Deliverables:** repo skeleton, documentation set, dataset in place
**Exit criterion:** fresh clone installs and `pytest` runs (even with zero tests)

---

## Phase 2: Raw Ingestion (Bronze)
**Goal:** Load all source data reliably into DuckDB.

**Tasks**
- [ ] Write `ingestion/config.py` (paths, expected files, expected columns)
- [ ] Write `ingestion/load_raw.py` with validation, logging, and idempotent loads
- [ ] Add `_loaded_at` and `_source_file` metadata columns
- [ ] Write `tests/test_ingestion.py`
- [ ] Add `make ingest`

**Deliverables:** `warehouse.duckdb` with 9 raw tables, ingestion logs, tests
**Exit criterion:** `make ingest` runs twice with identical results and logged row counts

---

## Phase 3: Exploratory Data Analysis
**Goal:** Understand the data and document its quirks before modeling.

**Tasks**
- [ ] `01_eda.ipynb`: row counts, null rates, date ranges, duplicates, outliers
- [ ] Identify the usable date window and data gaps
- [ ] Check order status distribution and delivery-date logic
- [ ] Document findings and cleaning decisions

**Deliverables:** EDA notebook, `docs/data_findings.md`
**Exit criterion:** a written list of data issues and the decision made for each

---

## Phase 4: Transformation & Data Modeling (Silver + Gold)
**Goal:** Build a tested star schema with dbt.

**Tasks**
- [ ] Configure dbt with the DuckDB profile
- [ ] Build `stg_*` models (clean, type, rename, deduplicate)
- [ ] Build `dim_customer`, `dim_product`, `dim_seller`, `dim_date`
- [ ] Build `fact_orders` and `fact_order_items`
- [ ] Add `unique`, `not_null`, `relationships`, and `accepted_values` tests
- [ ] Document all columns in `schema.yml`; generate dbt docs
- [ ] Add `make transform` and `make test`

**Deliverables:** gold star schema, passing tests, dbt lineage docs
**Exit criterion:** `dbt build` passes with 100% of tests green

---

## Phase 5: KPI Layer & Business Analytics
**Goal:** Turn the model into insights that support decisions.

**Tasks**
- [ ] Build `metrics_kpis` (revenue, orders, AOV, repeat rate, on-time %, review score)
- [ ] Cohort retention analysis
- [ ] RFM customer segmentation
- [ ] Delivery delay vs review score analysis
- [ ] Category and regional performance, seasonality
- [ ] Seller performance ranking
- [ ] Write each finding with a recommendation and estimated impact

**Deliverables:** analysis notebooks, `docs/insights.md`
**Exit criterion:** at least 8 of 10 business questions answered with evidence

---

## Phase 6: Demand Forecasting
**Goal:** Forecast weekly category demand and prove it beats baselines.

**Tasks**
- [ ] Build `mart_weekly_category_demand`
- [ ] Implement baselines: naive, seasonal naive, moving average
- [ ] Implement LightGBM (with lag and calendar features) and Prophet
- [ ] Implement rolling-origin backtesting
- [ ] Compute WAPE, MAPE, and bias per category
- [ ] Log runs to MLflow; select the best model per category with baseline fallback
- [ ] Write forecasts to the `forecast` schema
- [ ] Write `docs/forecast_report.md` (honest results, limitations)
- [ ] Add `tests/test_forecast_metrics.py` and `tests/test_backtest.py`

**Deliverables:** forecasting module, MLflow experiments, forecast tables, report
**Exit criterion:** documented WAPE comparison vs baseline; no leakage verified

---

## Phase 7: Dashboards
**Goal:** Make results accessible to non-technical users.

**Tasks**
- [ ] Executive Overview page (KPI cards, revenue trend, top categories, state map)
- [ ] Category Drill-down page (filters by date, category, state)
- [ ] Delivery Performance page (on-time %, delay vs reviews)
- [ ] Forecast page (history, forecast, uncertainty, accuracy)
- [ ] Add error handling and loading states
- [ ] Add `make dashboard`
- [ ] Capture screenshots for the README

**Deliverables:** working multi-page Streamlit app
**Exit criterion:** every dashboard number traces to a gold or forecast table with a documented definition

---

## Phase 8: Monitoring & Quality Hardening
**Goal:** Show production thinking.

**Tasks**
- [ ] Implement `forecasting/evaluate.py` with rolling WAPE and a drift flag
- [ ] Add pipeline run logging (duration, row counts, test status)
- [ ] Add data freshness and volume checks
- [ ] Add a short "what happens when it breaks" section to the docs
- [ ] Review the codebase against `rules.md`

**Deliverables:** monitoring module, run logs, hardening checklist
**Exit criterion:** an injected bad input (missing file, null key) fails loudly with a clear message

---

## Phase 9: Productionization (Docker, CI/CD, Orchestration)
**Goal:** Make the project reproducible with one command.

**Tasks**
- [ ] Write `Dockerfile` and `docker-compose.yml`
- [ ] Write `Makefile` target `make run` (ingest, transform, test, forecast)
- [ ] Add GitHub Actions: lint, type-check, pytest, dbt build
- [ ] (Optional) schedule the pipeline with Prefect
- [ ] (Optional) deploy the dashboard to Streamlit Community Cloud

**Deliverables:** Docker image, CI pipeline, one-command run
**Exit criterion:** a clean clone runs `make run` successfully, and CI is green on `main`

---

## Phase 10: Documentation, Business Summary & Presentation
**Goal:** Package the work so a reviewer understands it in five minutes.

**Tasks**
- [ ] Write the README (problem, architecture diagram, setup, screenshots, results, limitations)
- [ ] Finish `docs/data_dictionary.md`
- [ ] Draw `docs/architecture_diagram.png`
- [ ] Write the 1-page `docs/business_summary.md` with recommendations and estimated impact
- [ ] Record a 3-5 minute demo video or write a project walkthrough
- [ ] Prepare interview talking points (design decisions, trade-offs, what you would do next)
- [ ] Tag release `v1.0`

**Deliverables:** polished repo, business summary, demo
**Exit criterion:** someone unfamiliar with the project can run it and explain what it does

---

## Phase Overview

| Phase | Name | Key Output |
|---|---|---|
| 1 | Foundation & Business Framing | Repo, docs, dataset |
| 2 | Raw Ingestion | Bronze layer |
| 3 | EDA | Data findings |
| 4 | Transformation & Modeling | Tested star schema |
| 5 | KPI Layer & Analytics | Business insights |
| 6 | Demand Forecasting | Backtested forecasts |
| 7 | Dashboards | Streamlit app |
| 8 | Monitoring & Hardening | Drift checks, failure handling |
| 9 | Productionization | Docker, CI/CD |
| 10 | Documentation & Presentation | README, business summary |

**Scope control:** Phases 1-7 plus a basic Phase 9 make a strong MVP. Phases 8 and 10 turn it into a portfolio-grade project. Optional features (basket analysis, churn scoring, Prefect, live deployment) come only after v1.0.
