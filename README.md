# Retail Analytics & Demand Forecasting Platform

An end-to-end analytics project on a real marketplace dataset (Olist, Brazil, 2016-2018, about 100k orders). It covers ingestion, a tested dbt star schema, business analytics, a weekly demand forecast, and an interactive dashboard. The emphasis is on trustworthy numbers: every metric is defined once, tested, and traceable.

## Key findings
Window: Jan 2017 to Aug 2018. Money in BRL, delivered orders only. Details and caveats are in [`docs/insights.md`](docs/insights.md).

- **Scale:** BRL 13.2M delivered revenue, 96,211 delivered orders, 93,104 customers, average order value BRL 137.
- **Growth comes from new customers.** Only 3.0% of customers ordered more than once, and month-1 retention is 0.48%.
- **Late delivery is the biggest controllable problem.** Orders more than 3 days late average under 2.4 stars (4.29 on time). Late orders are 8% of deliveries but about a third of all 1-2 star reviews.
- **Delivery barely moves repeat buying.** The repeat-rate gap between late and on-time first deliveries is small and not statistically significant, so the case for faster delivery rests on reviews.
- **Forecasting: simple beats complex.** No model clearly beats a 4-week moving average on the holdout (WAPE 0.260 vs 0.286 for the selected policy and 0.356 for LightGBM). All models miss the Black Friday spike by 52% to 58%. See [`docs/forecast_report.md`](docs/forecast_report.md).
- **A data-quality finding shaped the work:** purchases are only fully captured through 2018-08-19, so August 2018 is flagged as incomplete everywhere ([`docs/data_findings.md`](docs/data_findings.md), finding 16).

## Architecture
```
Kaggle CSVs -> ingestion (validated, idempotent) -> DuckDB raw (bronze)
            -> dbt staging (silver) -> dbt marts (gold: star schema, KPIs, analysis tables)
            -> forecasting (walk-forward backtest, model selection) -> forecast schema
            -> Streamlit dashboard (reads marts and forecast only)
```
Design rules are in [`rules.md`](rules.md); the full layout is in [`architecture.md`](architecture.md).

## Quick start
Requirements: Python 3.10+, a Kaggle account for the dataset. On Windows without `make`, run the commands on the right.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env

# download the Olist dataset into data/raw/ (needs ~/.kaggle/kaggle.json)
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip

python -m ingestion.load_raw         # make ingest
cd dbt_project && dbt build && cd .. # make transform + test-dbt
python -m forecasting.train          # make forecast
streamlit run dashboard/app.py       # make dashboard
```
Close Jupyter and other DuckDB sessions before running the pipeline: DuckDB allows one writer.

## The dashboard
Four pages, all reading only the tested `marts` and `forecast` tables. A data-status block in the sidebar shows the analysis window, the date purchases are complete through, and when the forecast was generated:

| Page | What it shows |
|---|---|
| Executive Overview | KPI cards, revenue trend, new vs returning customers, top categories, state map |
| Category Drill-down | Filter by month, category and state; download the selection |
| Delivery Performance | On-time trend, review impact of lateness, regions, weakest sellers |
| Forecast | Category forecasts with error bands and baselines, accuracy, uncertainty |

Months with incomplete data are shown in grey. KPI tooltips carry the definitions from [`docs/kpi_definitions.md`](docs/kpi_definitions.md). If the warehouse is missing or locked, a page shows a short instruction, never a stack trace.

<!-- Add screenshots to docs/screenshots/ and link them here, for example:
![Executive overview](docs/screenshots/executive_overview.png) -->

## Testing and data quality
- **100+ dbt data tests:** keys, relationships, accepted values, and reconciliation tests that tie every mart back to the facts (nothing lost or double counted).
- **90+ Python tests:** ingestion, forecasting metrics, a counterfactual test that proves forecasts never use future data, end-to-end pipeline tests, and dashboard page tests.
- **A contract test** checks that every column the dashboard reads is documented in dbt or produced by the forecast pipeline, so a change to a mart cannot silently break a page.
- `ruff`, `mypy` and `pytest` run clean:
```bash
python -m pytest
ruff check . && ruff format --check .
mypy ingestion forecasting scripts dashboard
```

## Project structure
```
ingestion/      validated, idempotent CSV loading into DuckDB
dbt_project/    staging, marts, tests (the single source of metric definitions)
forecasting/    baselines, ETS, LightGBM, walk-forward backtest, model selection
dashboard/      Streamlit app (pages + components)
analytics/      exploration and analysis notebooks
scripts/        verification and summary helpers
tests/          Python tests
docs/           business case, data findings, KPI definitions, insights, forecast report
```

## Documentation
| Document | Purpose |
|---|---|
| [`PRD.md`](PRD.md) | what is built and for whom |
| [`architecture.md`](architecture.md) | flow, structure, tech stack |
| [`rules.md`](rules.md) | standards, error handling, boundaries |
| [`phases.md`](phases.md) | the build plan |
| [`docs/data_findings.md`](docs/data_findings.md) | data issues and the decision made for each |
| [`docs/kpi_definitions.md`](docs/kpi_definitions.md) | every metric defined |
| [`docs/insights.md`](docs/insights.md) | findings and recommendations |
| [`docs/forecast_report.md`](docs/forecast_report.md) | forecast method, results, limitations |

## Limitations
- One anonymised marketplace; 20 months of analysis, with a single holiday season.
- Late-August 2018 purchases are incompletely captured, so the most recent trend cannot be judged.
- Delivery effects are associations, not proven causes.
- The forecast is a statistical extrapolation with no knowledge of promotions; its holdout is only four forecast origins.
