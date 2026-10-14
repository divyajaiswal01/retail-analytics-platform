# Business Case

## Context
A mid-size online marketplace (modeled on the Olist Brazilian e-commerce dataset, 2016-2018) wants a single trusted view of sales, customers, and deliveries, plus a demand forecast to plan inventory and logistics.

## Problem
Teams work from disconnected reports. They cannot quickly answer what drives revenue, who the valuable customers are, how late deliveries affect satisfaction, or what demand to expect next.

## Stakeholders
| Stakeholder | Decision they make | What they need |
|---|---|---|
| Head of Sales | Where to invest for growth | Revenue, AOV, repeat rate, trends |
| Category Manager | What to stock and promote | Category/region performance, 8-week forecast |
| Supply Chain Lead | Where to fix delivery issues | On-time %, delay impact on reviews |

## Business Questions
1. Which categories and states drive the most revenue and growth?
2. How do revenue, orders, and AOV trend, and is there seasonality?
3. What is the repeat-purchase rate and how does retention evolve by cohort?
4. Who are the most valuable customers (RFM)?
5. What share of orders arrive late, and where?
6. How much do late deliveries reduce review scores?
7. Which sellers underperform on delivery or reviews?
8. What will weekly demand be by category over the next 8 weeks?
9. Which categories have the highest forecast uncertainty?
10. What is the estimated revenue impact of improving on-time delivery?

## KPI Definitions (draft; finalize in Phase 5)
| KPI | Definition |
|---|---|
| Revenue | Sum of item price for delivered orders (BRL), excluding freight |
| Orders | Count of distinct delivered orders |
| AOV | Revenue / Orders |
| Repeat rate | Customers with 2+ orders / all customers (by `customer_unique_id`) |
| On-time delivery % | Delivered orders with delivery date <= estimated date / delivered orders |
| Avg review score | Mean review score (1-5) per order |
| WAPE | Sum of absolute forecast errors / sum of actuals |

## Success Criteria
- Forecast WAPE at least 10% better than the naive baseline
- All dbt tests passing
- One-command pipeline run from a clean clone
- At least 8 of 10 questions answered with a recommendation

## Out of Scope
Real-time analytics, SKU-level forecasting, paid cloud infrastructure.
