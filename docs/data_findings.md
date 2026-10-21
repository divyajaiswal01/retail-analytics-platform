# Data Findings & Decisions

**Source:** `analytics/notebooks/01_eda.ipynb` run on the real Olist dataset (summary cell output).
**Purpose:** every cleaning rule in dbt (Phase 4) traces back to a row in this table.
**Currency:** BRL. **Not reviewed yet:** notebook section 2 (null rates) and the full review-score distribution; add notes below if they reveal anything.

---

## 1. Dataset snapshot

| Item | Value |
|---|---|
| Tables loaded | 9 |
| Total orders | 99,441 |
| Order items | 112,650 |
| Customers (`customer_id`) / real people (`customer_unique_id`) | 99,441 / 96,096 |
| Products / sellers | 32,951 / 3,095 |
| First order month | 2016-09 |
| Last order month | 2018-10 |
| **Analysis window chosen** | **2017-01-01 to 2018-08-31 (20 full months)** |
| Reason for window | 2016 has only 329 orders in 3 months (Nov 2016 is missing entirely). Sep and Oct 2018 have 16 and 4 orders, none delivered, so the data effectively ends in Aug 2018. Jan 2017 (800 orders) is a ramp-up month but is kept so the window covers Nov 2017. |

Window is a dbt variable (`analysis_start_date`, `analysis_end_date` in `dbt_project.yml`). Rows outside it are kept in the facts and flagged `in_analysis_window = false`.

---

## 2. Issues & decisions

| # | Area | Evidence (real numbers) | Decision | Implemented in |
|---|---|---|---|---|
| 1 | Customer identity | 99,441 `customer_id` but only 96,096 `customer_unique_id`: 3,345 repeat IDs | Use `customer_unique_id` as the customer key for repeat rate, RFM, cohorts | `dim_customer`, `fact_orders.customer_key` |
| 2 | Sparse months | 2016: 4 / 324 / 1 orders (Sep, Oct, Dec). 2018-09: 16, 2018-10: 4 | Analysis window 2017-01 to 2018-08; out-of-window rows flagged, not deleted | `fact_orders`, `fact_order_items` |
| 3 | Order status | delivered 96,478 (97.02%); shipped 1,107; canceled 625; unavailable 609; invoiced 314; processing 301; created 5; approved 2 | Revenue counts delivered orders only (`delivered_revenue`); other statuses kept with `order_status` | `fact_orders` |
| 4 | Delivered, no date | 8 delivered orders have no delivery date | Excluded from delivery days and on-time %; still count toward revenue | `fact_orders.delivery_days`, `is_late` |
| 5 | Dates out of logic | 0 delivered-before-purchase; but 6 non-delivered orders have a delivery date | No fix needed for the first; delivery metrics use delivered status only, so the 6 are ignored; a test guards negative days | `fact_orders`, test `assert_no_negative_delivery_days` |
| 6 | Multiple payments | 96,479 orders have 1 payment; 2,961 have 2 to 29; 1 order has none | Aggregate payments to one row per order before joining (otherwise revenue is double counted) | `fact_orders`, test `assert_payments_not_double_counted` |
| 7 | Orders without items | 775 orders (0.78%); 768 orders without reviews | Keep in `fact_orders` with `item_count = 0`; item-level analysis uses `fact_order_items` | `fact_orders` |
| 8 | Payment vs items | 249 of 98,665 orders (0.25%) differ by more than 1.00 BRL | Revenue = sum of item price (excluding freight); payment totals kept as a separate column | `fact_orders` |
| 9 | Duplicate reviews | `review_id` repeats (814 duplicate rows); 543 orders have 2 reviews and 4 have 3 | Keep the most recent review per order (answer time, then creation time, then `review_id`) | `stg_reviews`; unique test on `order_id` |
| 10 | Missing category | 610 products (1.85%) have no category | Map to `unknown` rather than dropping products | `dim_product` |
| 11 | Untranslated categories | 2 categories (13 products): `portateis_cozinha_e_preparadores_de_alimentos` (10), `pc_gamer` (3) | Add manual English names | `stg_category_translation` |
| 12 | Product weights | 2 missing, 4 zero | Treat zero as NULL; no imputation | `stg_products` |
| 13 | Outliers | Price: min 0.85, none zero or negative, p99 890, max 6,735. Freight: 383 rows at zero. Payment value: 9 rows at zero | Keep all values; nothing silently deleted. Zero freight is probably free shipping (hypothesis, not verified) | `stg_order_items`, `stg_order_payments` |
| 14 | Orphan keys | 0 orphans on every relationship except products to category translation (13) | Relationship tests enforce this going forward; any future orphan fails the build | `schema.yml` tests |
| 15 | Geolocation grain | 1,000,163 rows for 19,015 zip prefixes (about 53 per zip) | Reduce to one row per zip using median coordinates; not joined into marts yet (map uses state) | `stg_geolocation` |
| 16 | Data completeness at the end | Daily items fall from 289 (Aug 17) and 283 (Aug 20) to 161 (Aug 23), 75 (Aug 25) and 16 (Aug 29), with no rows for Aug 30-31. All-status items per week: 2,054 (week of Aug 13) vs 1,192 (week of Aug 20). The final week has the HIGHEST delivered share (99.6%), which rules out delivery lag as the cause | Treat purchase data as reliable only through 2018-08-19 (`data_complete_through`). Weekly demand stops at the week ending Aug 19. August 2018 monthly figures are flagged `is_complete_month = false` and understated by roughly a fifth (estimate). The analysis window itself is unchanged | `dbt_project.yml`, `mart_weekly_category_demand`, `metrics_kpis` |

---

## 3. Data quality notes for the README

- Coverage is Sep 2016 to Oct 2018, but only Jan 2017 to Aug 2018 is analysed (20 months), and purchases are fully captured only through 2018-08-19 (finding #16).
- The 20-month window contains only one holiday season (Nov 2017 spike: 7,544 orders vs 4,631 in Oct), so **yearly seasonality cannot be learned reliably**. A 52-week seasonal baseline is only possible from the second year onward. State this in the forecast report instead of overclaiming.
- Data is anonymised and from a single Brazilian marketplace; all money is BRL, not converted.
- Customers are identified by `customer_unique_id`; repeat purchasing is rare (3,345 of 99,441 `customer_id` rows, 3.4%, are extra IDs for returning customers), so repeat rate and cohort retention will be low and noisy.
- 97% of orders are delivered, so status effects on revenue are small.

## 4. Open questions

- Review the null-rate table (notebook section 2) and the review score distribution; add anything surprising as new rows above.
- Confirm after the first full `dbt build` that all tests pass on the real data.
