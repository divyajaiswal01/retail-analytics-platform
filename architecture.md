# Architecture: Retail Analytics & Demand Forecasting Platform

---

## 1. App Flow & Architecture

### High-Level Flow

```
 ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
 │ Kaggle CSVs │──▶│  Ingestion   │──▶│   DuckDB      │──▶│ dbt Staging  │
 │ (9 tables)  │   │ load_raw.py  │   │ raw (bronze)  │   │ (silver)     │
 └─────────────┘   └──────────────┘   └───────────────┘   └──────┬───────┘
                                                                 │
                                                                 ▼
 ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
 │  Streamlit  │◀──│ Forecast     │◀──│ Gold marts    │◀──│ dbt Marts +  │
 │  Dashboards │   │ outputs +    │   │ star schema + │   │ dbt tests    │
 │             │   │ MLflow       │   │ metrics       │   │ (gold)       │
 └─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘
```

### Layers (Medallion Architecture)

| Layer | Schema | Purpose | Rules |
|---|---|---|---|
| **Bronze** | `raw` | Untouched copy of source CSVs | No transformation; add `_loaded_at` and `_source_file` |
| **Silver** | `staging` | Cleaned, typed, renamed, deduplicated | One model per source table; `stg_` prefix |
| **Gold** | `marts` | Star schema + business metrics | `fact_` and `dim_` prefixes; fully tested |
| **Serving** | `forecast` | Forecast outputs and accuracy logs | Written by Python, read by dashboard |

### Pipeline Stages

1. **Ingest:** `load_raw.py` reads CSVs and writes to `raw.*`, logs row counts.
2. **Transform:** `dbt run` builds staging then marts.
3. **Test:** `dbt test` validates keys, nulls, relationships, accepted values.
4. **Analyze:** notebooks and SQL produce cohort, RFM, and delivery insights.
5. **Forecast:** `train.py` reads weekly category demand, fits models, backtests, logs to MLflow, writes `forecast.*`.
6. **Serve:** Streamlit reads gold and forecast tables, renders dashboards.
7. **Monitor:** `evaluate.py` computes rolling WAPE and flags drift.

### Star Schema

```
                 dim_date
                    │
 dim_customer ── fact_orders ── dim_seller
                    │
             fact_order_items ── dim_product
```

| Table | Grain | Key Columns |
|---|---|---|
| `fact_orders` | One row per order | order_id, customer_key, date_key, status, payment_total, delivery_days, is_late, review_score |
| `fact_order_items` | One row per order item | order_id, item_id, product_key, seller_key, price, freight_value |
| `dim_customer` | One row per unique customer | customer_key, customer_unique_id, city, state |
| `dim_product` | One row per product | product_key, category_en, weight_g, dimensions |
| `dim_seller` | One row per seller | seller_key, city, state |
| `dim_date` | One row per day | date_key, date, week, month, quarter, year, is_weekend |

---

## 2. Folder & File Structure

```
retail-analytics-platform/
├── README.md
├── PRD.md
├── architecture.md
├── rules.md
├── phases.md
├── Makefile                      # make setup | ingest | transform | test | forecast | dashboard | run
├── Dockerfile
├── docker-compose.yml
├── requirements.txt              # pinned versions
├── pyproject.toml                # ruff, mypy, pytest config
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
│
├── .github/
│   └── workflows/
│       └── ci.yml                # lint, tests, dbt build
│
├── data/
│   ├── raw/                      # source CSVs (gitignored)
│   └── warehouse.duckdb          # gitignored
│
├── ingestion/
│   ├── __init__.py
│   ├── config.py                 # paths, table list, schemas
│   ├── load_raw.py               # CSV -> DuckDB raw
│   └── logger.py
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_orders.sql
│   │   │   ├── stg_order_items.sql
│   │   │   ├── stg_customers.sql
│   │   │   ├── stg_products.sql
│   │   │   ├── stg_sellers.sql
│   │   │   ├── stg_payments.sql
│   │   │   ├── stg_reviews.sql
│   │   │   └── schema.yml
│   │   ├── marts/
│   │   │   ├── dim_customer.sql
│   │   │   ├── dim_product.sql
│   │   │   ├── dim_seller.sql
│   │   │   ├── dim_date.sql
│   │   │   ├── fact_orders.sql
│   │   │   ├── fact_order_items.sql
│   │   │   ├── metrics_kpis.sql
│   │   │   ├── metrics_summary.sql
│   │   │   ├── mart_customer_rfm.sql
│   │   │   ├── mart_cohort_retention.sql
│   │   │   ├── mart_delivery_impact.sql
│   │   │   ├── mart_delivery_vs_repeat.sql
│   │   │   ├── mart_category_performance.sql
│   │   │   ├── mart_state_performance.sql
│   │   │   ├── mart_seller_performance.sql
│   │   │   ├── mart_weekly_category_demand.sql
│   │   │   ├── mart_sales_cube.sql          # additive month x category x state, feeds the drill-down
│   │   │   └── schema.yml
│   ├── tests/                    # custom singular tests
│   └── macros/
│
├── analytics/
│   ├── sql/                      # reusable analysis queries
│   └── notebooks/
│       ├── 01_eda.ipynb
│       ├── 02_cohort_retention.ipynb
│       ├── 03_rfm_segmentation.ipynb
│       ├── 04_delivery_impact.ipynb
│       ├── 05_category_region_seller.ipynb
│       └── 06_forecast_review.ipynb
│
├── forecasting/
│   ├── __init__.py
│   ├── data.py                   # load weekly demand
│   ├── baselines.py              # naive, seasonal naive, moving average
│   ├── models.py                 # LightGBM / Prophet wrappers
│   ├── backtest.py               # rolling-origin cross-validation
│   ├── metrics.py                # MAPE, WAPE, bias
│   ├── train.py                  # CLI entry point
│   └── evaluate.py               # drift monitoring
│
├── dashboard/
│   ├── app.py                    # Streamlit entry: navigation + sidebar data status
│   ├── pages/
│   │   ├── 1_Executive_Overview.py
│   │   ├── 2_Category_Drilldown.py
│   │   ├── 3_Delivery_Performance.py
│   │   └── 4_Forecast.py
│   └── components/
│       ├── data.py               # cached read-only warehouse access, friendly errors
│       ├── queries.py            # named SELECTs on marts / forecast tables only
│       ├── charts.py             # Plotly figure builders (draw only, no calculations)
│       ├── brazil_map.py         # offline tile-grid map of Brazilian states
│       ├── definitions.py        # KPI tooltips mirroring docs/kpi_definitions.md
│       └── ui.py                 # formats and Streamlit-version-safe helpers
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_forecast_metrics.py
│   └── test_backtest.py
│
├── docs/
│   ├── business_case.md
│   ├── data_dictionary.md
│   ├── architecture_diagram.png
│   ├── forecast_report.md
│   └── business_summary.md       # 1-page recommendations
│
└── mlruns/                       # MLflow local store (gitignored)
```

---

## 3. Tech Stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Standard for analytics and ML |
| Warehouse | DuckDB | Free, fast, file-based, SQL-native, no server |
| Transformation | dbt-duckdb | Modular SQL, tests, lineage, docs |
| Data Quality | dbt tests (+ Great Expectations optional) | Declarative, CI-friendly |
| Analysis | pandas, SQL, plotly | Familiar, interview-friendly |
| Forecasting | LightGBM, Prophet, statsmodels | Strong baselines plus ML comparison |
| Experiment Tracking | MLflow (local) | Industry standard |
| Dashboard | Streamlit + Plotly (Power BI optional second view) | Fast to build, deployable free |
| Orchestration | Makefile (MVP), Prefect (optional) | Start simple |
| Containerization | Docker | Reproducible environment |
| CI/CD | GitHub Actions | Free, widely recognized |
| Code Quality | ruff, mypy, pytest, pre-commit | Enforce standards |
| Version Control | Git + GitHub | Portfolio visibility |

---

## 4. Configuration & Secrets

- All paths and settings in `ingestion/config.py` and `.env`
- `.env.example` is committed; `.env` is gitignored
- Kaggle credentials stay in `~/.kaggle/kaggle.json`, never in the repo

---

## 5. Observability

- Structured logging (timestamp, stage, row counts, duration) for every pipeline step
- dbt test results surfaced in CI
- Forecast accuracy logged per run; drift flagged when rolling WAPE exceeds baseline by a set threshold
