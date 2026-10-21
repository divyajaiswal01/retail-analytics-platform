# KPI Definitions

Single source of truth for every metric on a dashboard or in an analysis. Money is in **BRL**.
All KPIs use the **analysis window** (`analysis_start_date` to `analysis_end_date` in `dbt_project.yml`, currently 2017-01-01 to 2018-08-31) unless stated.

## Rules that apply to every KPI
- **Revenue counts delivered orders only**, using item price and excluding freight.
- **Customers** are real people (`customer_unique_id`), not per-order `customer_id`.
- **Months** are purchase months (the order date, not the delivery date).
- Months that extend past `data_complete_through` (currently 2018-08-19) are flagged `is_complete_month = false` in `metrics_kpis`; their totals are understated and must not be read as a trend.
- Delivery metrics need a delivered order **with** a delivery date; the few without are excluded from them but still count toward revenue.

## KPI table

| KPI | Definition | Where it is computed |
|---|---|---|
| Delivered revenue | Sum of item prices of delivered orders, excluding freight | `metrics_kpis`, `metrics_summary`, `fact_orders.delivered_revenue` |
| Orders placed | Orders of any status | `metrics_kpis.orders_placed` |
| Delivered orders | Orders with status `delivered` | `metrics_kpis`, `metrics_summary` |
| AOV | Delivered revenue / delivered orders that have revenue | `metrics_kpis.aov`, `metrics_summary.aov` |
| Unique customers | Distinct customers with a delivered order in the period | `metrics_kpis`, `metrics_summary.customers` |
| New customers | Customers whose first-ever delivered order falls in the month | `metrics_kpis.new_customers` |
| Returning customers | Unique customers minus new customers | `metrics_kpis.returning_customers` |
| Repeat rate | Customers with 2+ delivered orders in the window / customers with 1+ | `metrics_summary.repeat_rate_pct` |
| On-time delivery % | Delivered orders delivered on or before the estimated date / delivered orders with a delivery date | `metrics_kpis`, `metrics_summary`, state and seller marts |
| Average delivery days | Mean days from purchase to delivery | same as above |
| Average review score | Mean score (1-5) of the most recent review per order | same as above |
| Revenue MoM growth | Change in delivered revenue vs the previous month | `metrics_kpis.revenue_mom_growth_pct` |
| Category YoY growth | Revenue in the `yoy_current` period vs the same dates one year earlier | `mart_category_performance` |
| Cohort retention | Share of a first-order-month cohort that orders again N months later | `mart_cohort_retention` |
| RFM segment | Rule-based segment from recency, frequency and spend scores | `mart_customer_rfm` |
| Forecast WAPE | Sum of absolute forecast errors / sum of actuals (Phase 6) | forecasting module |

## Known limitations
- **Repeat rate is low and right-censored:** customers acquired late in the window have had less time to return.
- **Seller attribution:** orders with several sellers count toward each seller's lateness and reviews.
- **Delivery impact is association, not causation:** late orders may differ in distance, product or seller.
- **August 2018 is incomplete:** purchase capture thins out after about Aug 19, so its totals, and any growth figure that includes it, are understated.
- **One holiday season** falls inside the window, so seasonality cannot be separated from a single spike.
