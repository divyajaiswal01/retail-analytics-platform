# PRD: Retail Analytics & Demand Forecasting Platform

**Version:** 1.0  **Status:** Draft  **Owner:** <DIVYA JAISWAL>

---

## 1. What to Build

An end-to-end analytics platform for a mid-size online marketplace. It ingests raw order data, transforms it into a tested star schema, answers key business questions, forecasts category-level demand, and serves everything through dashboards, all runnable with one command.

**Dataset:** Olist Brazilian E-commerce (Kaggle, ~100k orders, 9 relational tables).

### Problem Statement
Sales, supply chain, and category teams lack a single trusted source of truth. They cannot easily see what drives revenue, which customers are valuable, how late deliveries hurt satisfaction, or how much stock to prepare for the coming weeks.

### Goals
1. Provide one trusted, tested data model for sales, customers, products, and deliveries.
2. Answer 8-10 concrete business questions with decision-ready insights.
3. Forecast weekly demand per product category for the next 8 weeks, beating a naive baseline.
4. Deliver an executive dashboard and a drill-down operational dashboard.
5. Make the whole pipeline reproducible, tested, and documented.

### Non-Goals
- Real-time or streaming analytics
- SKU-level forecasting (data is too sparse; forecasting is category x week)
- Customer-facing features or transactional systems
- Paid cloud infrastructure

---

## 2. Targeted Users

| Persona | Role | Needs | Primary Output |
|---|---|---|---|
| **Head of Sales** | Executive | Revenue, growth, AOV, repeat rate at a glance | Executive dashboard |
| **Category Manager** | Operational | Category/region performance, demand forecast, seasonality | Drill-down dashboard, forecast table |
| **Supply Chain Lead** | Operational | On-time delivery %, late-delivery impact on reviews | Delivery performance view |
| **Data Analyst (secondary)** | Technical | Clean documented tables, data dictionary | Gold-layer marts, docs |
| **Hiring Manager / Reviewer** | Evaluator | Clear business case, clean repo, working demo | README, demo link |

---

## 3. Features

### Must Have (MVP)
| ID | Feature | Acceptance Criteria |
|---|---|---|
| F1 | Automated raw ingestion | All 9 CSVs load into DuckDB `raw` schema; row counts logged; re-runs are idempotent |
| F2 | Star schema (gold layer) | `fact_orders`, `fact_order_items`, `dim_customer`, `dim_product`, `dim_seller`, `dim_date` built via dbt |
| F3 | Data quality tests | Not-null, unique, relationship, and accepted-values tests pass in CI |
| F4 | KPI layer | Revenue, orders, AOV, repeat rate, on-time delivery %, avg review score computed in one metrics model |
| F5 | Business analyses | Cohort retention, RFM segmentation, delivery-vs-review impact, category and regional performance |
| F6 | Demand forecast | Weekly category forecast, 8-week horizon, compared against naive and seasonal-naive baselines |
| F7 | Executive dashboard | KPI cards, revenue trend, top categories, region map |
| F8 | Drill-down dashboard | Filters by date, category, state; forecast vs actual view |
| F9 | One-command run | `make run` executes ingest, transform, test, and forecast |

### Should Have
| ID | Feature |
|---|---|
| F10 | MLflow experiment tracking for forecast models |
| F11 | Forecast accuracy monitoring (rolling MAPE/WAPE with drift flag) |
| F12 | Docker image for pipeline and dashboard |
| F13 | GitHub Actions CI (lint, tests, dbt build) |
| F14 | Data dictionary and architecture diagram |

### Could Have
| ID | Feature |
|---|---|
| F15 | Market basket analysis |
| F16 | Churn-risk scoring for repeat customers |
| F17 | Scheduled runs via Prefect or Airflow |
| F18 | Deployed live demo (Streamlit Community Cloud) |

---

## 4. Business Questions to Answer

1. Which categories and states drive the most revenue and growth?
2. How have revenue, orders, and AOV trended over time? Is there seasonality?
3. What is the repeat-purchase rate and how does retention evolve by cohort?
4. Who are the most valuable customers (RFM segments)?
5. What share of orders arrive late, and where?
6. How much do late deliveries reduce review scores?
7. Which sellers underperform on delivery or reviews?
8. What will demand be by category over the next 8 weeks?
9. Which categories show the highest forecast uncertainty?
10. What is the estimated revenue impact of improving on-time delivery?

---

## 5. Success Metrics

| Metric | Target |
|---|---|
| Forecast WAPE vs naive baseline | At least 10% improvement |
| dbt tests passing | 100% |
| Pipeline run from clean clone | One command, under 10 minutes |
| Business questions answered with a recommendation | 8 of 10 |
| Documentation completeness | README, PRD, architecture, data dictionary all present |

---

## 6. Non-Functional Requirements

- **Reproducibility:** pinned dependencies, deterministic seeds, no manual steps
- **Reliability:** pipeline fails loudly with clear logs, never silently
- **Performance:** full pipeline runs on a laptop with 8 GB RAM
- **Maintainability:** modular code, typed Python, documented SQL models
- **Cost:** zero (all open-source or free tier)

---

## 7. Assumptions & Risks

| Risk / Assumption | Mitigation |
|---|---|
| Data covers only 2016-2018 and has gaps in 2016 | Restrict analysis window to well-populated period; document it |
| Sparse data at product level | Aggregate to category x week |
| Dataset is Brazilian; currency is BRL | Label all values in BRL; do not convert silently |
| Scope creep | Stick to MVP first; Should/Could only after Phase 7 |
| Forecast may not beat baseline for some categories | Report honestly; fall back to baseline per category |

---

## 8. Deliverables

- Working pipeline and warehouse
- Two dashboards
- Forecasting module with evaluation report
- Documentation set (PRD, architecture, rules, phases, data dictionary)
- 1-page business summary with recommendations
