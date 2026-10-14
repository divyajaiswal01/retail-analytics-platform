# Rules: Retail Analytics & Demand Forecasting Platform

These rules apply to every contributor, including AI assistants. If a rule must be broken, document why in the pull request.

---

## 1. What to Use

### Languages & Core Tools
| Purpose | Use |
|---|---|
| Language | Python 3.11 |
| Warehouse | DuckDB |
| Transformations | dbt-duckdb (SQL only for business logic) |
| Dashboard | Streamlit + Plotly |
| Tracking | MLflow (local) |
| Packaging | `requirements.txt` with pinned versions |

### Approved Libraries
| Area | Libraries |
|---|---|
| Data | `pandas`, `duckdb`, `pyarrow` |
| Forecasting | `lightgbm`, `prophet`, `statsmodels`, `scikit-learn` |
| Viz | `plotly`, `streamlit` |
| Quality | `pytest`, `ruff`, `mypy`, `pre-commit` |
| Config | `python-dotenv`, `pydantic` (for config validation) |
| Logging | Python standard `logging` module |

Any library not on this list needs a one-line justification in the PR before it is added.

### Coding Standards
- Type hints on all function signatures
- Docstrings on all public functions (what, args, returns)
- `ruff` for lint and format; `mypy` must pass
- Functions do one thing; keep them under about 40 lines
- SQL: lowercase keywords, CTEs over nested subqueries, one model per file
- Naming: `snake_case` for Python and SQL; prefixes `stg_`, `dim_`, `fact_`, `mart_`

### Data & Modeling Standards
- Every model has a primary key with `unique` and `not_null` tests
- Every foreign key has a `relationships` test
- Every column in marts is documented in `schema.yml`
- All money values are labeled BRL; never convert currency silently
- Forecasts are always compared to a naive and seasonal-naive baseline
- Time-series validation uses **rolling-origin (walk-forward)** splits only
- Random seeds set explicitly for every stochastic step

### Git Standards
- Small commits with clear messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- Feature branches; merge to `main` only when CI passes
- One phase = one milestone tag (e.g., `v0.1-phase1`)

---

## 2. What to Avoid

- **No data leakage:** never fit scalers, encoders, or models on future data; never shuffle time-series splits
- **No random train/test split** for forecasting
- **No hardcoded paths, credentials, or magic numbers**; use config and `.env`
- **No business logic in the dashboard**; the dashboard only reads gold and forecast tables
- **No transformation in the raw layer**; bronze stays untouched
- **No `SELECT *`** in dbt models
- **No manual data edits** in the warehouse; every change comes from code
- **No committing** raw data, `.duckdb` files, `mlruns/`, or secrets
- **No notebooks as production code**; logic is moved into modules once it works
- **No silent failures:** no bare `except:`, no swallowed exceptions
- **No unexplained metrics:** every number on a dashboard has a definition in `data_dictionary.md`
- **No overclaiming:** do not report forecast gains that backtests do not support
- **No SKU-level forecasting** (data too sparse); use category x week
- **No over-engineering:** no Kubernetes, Spark, or streaming for this scope

---

## 3. Error Handling

### Principles
1. Fail fast and loudly on bad inputs; never continue with corrupted data.
2. Handle only errors you can meaningfully handle; let the rest propagate.
3. Every error message states what failed, where, and what to check.

### Rules by Layer
| Layer | Rule |
|---|---|
| **Ingestion** | Verify files exist and expected columns match before loading; raise a clear error listing missing files or columns; log row counts after each table; loading must be idempotent (drop and recreate or upsert) |
| **dbt** | A failing test fails the pipeline; do not mark tests as warn-only unless documented |
| **Forecasting** | Validate input has no gaps or duplicates per category-week; if a model fails for a category, log it and fall back to the baseline for that category; never drop the category silently |
| **Dashboard** | Wrap data loads in `try/except`; show a user-friendly error with `st.error`; log the technical detail; never display a raw stack trace |
| **CLI scripts** | Non-zero exit code on failure so CI and `make` detect it |

### Logging
- Use the `logging` module, not `print`
- Format: `timestamp | level | module | message`
- Levels: `INFO` for stage start/finish and row counts, `WARNING` for fallbacks, `ERROR` for failures
- Never log secrets or personal data

---

## 4. Libraries & Dependency Rules

- Pin exact versions in `requirements.txt`
- Add dependencies only when needed; remove unused ones
- Re-run the full test suite after any dependency change
- Prefer standard library or already-approved packages over new ones

---

## 5. Boundaries for AI

### AI May
- Generate boilerplate, scaffolding, and first drafts of code and SQL
- Explain errors and suggest fixes
- Write tests, docstrings, and documentation
- Suggest refactors and review code against these rules
- Propose analysis approaches and visualizations

### AI Must
- Follow every rule in this document
- State assumptions explicitly when requirements are ambiguous
- Keep changes scoped to the current phase and the files requested
- Provide runnable code with imports, types, and error handling
- Flag uncertainty instead of guessing, especially about metrics, dates, or data meaning
- Recommend a test for any non-trivial logic it writes

### AI Must Not
- Invent data, columns, metrics, or results; if it has not run, it must say so
- Fabricate library functions or APIs; verify against documentation when unsure
- Report model performance numbers it has not computed
- Add new dependencies, tables, or folders outside the documented structure without approval
- Modify the raw layer, CI configuration, or these rule files without being asked
- Touch or request credentials, API keys, or personal data
- Skip tests or lower thresholds to make a pipeline pass
- Make business recommendations unsupported by the data

### Human Responsibilities
- Review and understand all AI-generated code before committing
- Run tests locally before every commit
- Own the final insights and recommendations
- Be able to explain every design decision in an interview
- Decide when to deviate from the plan

### Working Protocol with AI
1. Start each session by sharing the current phase from `phases.md` and relevant files.
2. Ask for one small, well-defined task at a time.
3. Run the output; paste back real errors and real results.
4. Commit only after tests pass.
5. Update docs when behavior changes.
