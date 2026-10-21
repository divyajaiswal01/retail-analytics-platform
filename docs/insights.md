# Business Insights & Recommendations

**Window:** 2017-01-01 to 2018-08-31 (20 months). **Currency:** BRL. **Scope:** delivered orders only.
**Source:** `python -m scripts.phase5_summary` on the real warehouse, plus figures derived from it (stated where used).
**Status:** first draft for the project owner to review. Items marked *(hypothesis)* are not proven by the data. Items marked *(derived)* are arithmetic on the numbers shown, not new queries.

## Headline numbers

| Metric | Value |
|---|---|
| Delivered revenue | BRL 13,181,027 |
| Delivered orders | 96,211 |
| Average order value | BRL 137.00 |
| Customers | 93,104 |
| Repeat rate (2+ delivered orders) | 3.00% (2,789 customers) |
| On-time delivery | 91.87% |
| Average delivery time | 12.5 days |
| Average review score | 4.16 |

**The story in four sentences.** The marketplace grew very fast through 2017, then slowed to roughly 6,000 to 7,000 delivered orders a month in the first half of 2018 (the data thins out after about Aug 19, 2018, so the most recent trend cannot be judged). Almost every customer buys once, so growth comes from acquiring new customers, not from retention. Late delivery is the biggest controllable problem: orders more than 3 days late average under 2.4 stars. Better on-time delivery is worth pursuing for reviews and reputation, but the data shows no meaningful effect on repeat revenue.

---

## Q1. Which categories and states drive revenue and growth?
**Source:** `mart_category_performance`, `mart_state_performance`

- **Finding (categories):** The top 10 categories make up 62.5% of revenue. The largest are health_beauty (9.3%, BRL 1.23M), watches_gifts (8.8%) and bed_bath_table (7.8%).
- **Finding (growth):** Revenue for Jan-Aug 2018 was 141% higher than Jan-Aug 2017 *(derived from the monthly table: BRL 7.22M vs 2.99M)*. This is slightly understated, because late August 2018 is incompletely captured (see Q2). Against that market rate:
  - Faster than the market: watches_gifts (+242%), health_beauty (+210%), housewares (+207%), auto (+174%).
  - Roughly in line: sports_leisure (+139%), computers_accessories (+131%).
  - Slower: furniture_decor (+123%), bed_bath_table (+109%), garden_tools (+54%), and cool_stuff (+10%).
- **Finding (states):** SP generates 38.4% of revenue, RJ 13.3%, MG 11.7%. The top 3 states are 63.4% and the top 5 are 73.9% *(derived)*.
- **Recommendation:** Prioritise inventory and marketing for the categories growing faster than the market. Investigate cool_stuff: it was fifth largest in the prior period and is now eighth.
- **Estimated impact and assumptions:** If cool_stuff had grown at the market rate, its Jan-Aug 2018 revenue would be about BRL 497K instead of BRL 228K, a gap of roughly BRL 270K *(derived, illustrative)*. This is not a forecast of recoverable revenue; it assumes the category "should" track the market, which may not hold.

## Q2. How do revenue, orders and AOV trend? Is there seasonality?
**Source:** `metrics_kpis`

- **Finding (trend):** Monthly revenue rose from BRL 112K (Jan 2017) to BRL 978K (May 2018). Delivered orders were roughly flat at 6,100 to 7,100 a month from Jan to Jul 2018. **August 2018 must not be read as a decline:** daily items fall from about 290 on Aug 17 to 161 on Aug 23 and 16 on Aug 29, with no rows for Aug 30-31, which is the signature of incomplete data capture, not of falling demand. The August figures are therefore understated (roughly a fifth of the month's items are missing, *derived estimate*). Weekly items in late July to mid August (2,054 to 2,305) were in fact higher than in June (1,622 to 1,729), so there is no evidence of a decline.
- **Finding (AOV):** AOV stayed in a narrow band of BRL 126 to 149 all period, so growth came from order volume, not basket size.
- **Finding (seasonality):** November 2017 delivered 7,289 orders, 63% more than October, with revenue up 52% *(derived)*. Only one November is in the window, so this cannot be separated from a one-off event. *(Hypothesis: the spike is Black Friday week; check daily order counts to confirm.)*
- **Recommendation:** Treat the first half of 2018 as a slowdown from 2017's growth and test acquisition channels; the data cannot show what happened after about Aug 19. Plan capacity for a November peak every year (see Q5).
- **Estimated impact and assumptions:** none claimed; the data cannot support a seasonal estimate from one year.

## Q3. What is the repeat-purchase rate and how does retention evolve?
**Source:** `metrics_summary`, `mart_cohort_retention`

- **Finding:** 3.00% of customers ordered more than once. Retention after the first month is very low: 0.48% in month 1, 0.26% in month 3, 0.23% in month 6, 0.17% in month 12. Returning customers are only about 2.6% of monthly buyers (166 of 6,310 in Aug 2018) *(derived)*.
- **Finding:** Later-month figures rest on fewer cohorts (8 cohorts at month 12) and are noisier.
- **Recommendation:** Treat this as an acquisition-driven business. If a retention test is run (for example a post-purchase email), use a holdout group so the effect can actually be measured.
- **Estimated impact and assumptions:** Even doubling the repeat rate, with each extra repeat customer placing one more order at the average value, would add about BRL 382K, or 2.9% of window revenue *(derived, illustrative)*. Retention is a modest lever here.

## Q4. Who are the most valuable customers (RFM)?
**Source:** `mart_customer_rfm`

- **Finding:** Two high-value segments, "Recent high-value" (15.7% of customers) and "Lapsed high-value" (14.9%), together hold 58.4% of revenue from 30.6% of customers *(derived)*. Repeat customers (active plus lapsed) are 3.0% of customers and 5.5% of revenue.
- **Recommendation:** Run a win-back test on the 13,912 "Lapsed high-value" customers, with a holdout. Nurture "Recent high-value" customers (14,611) toward a second order.
- **Estimated impact and assumptions:** Each 1% of the lapsed high-value group that reorders is 139 orders, about BRL 19K at the average order value or BRL 38K at that group's historical spend; a 5% response would be BRL 95K to 191K *(derived, illustrative)*. Because natural repeat is below 0.5% a month, the real uplift must be measured against a holdout; do not assume these responses.

## Q5. What share of orders arrive late, and where?
**Source:** `metrics_summary`, `mart_state_performance`, `metrics_kpis`

- **Finding (overall):** 8.1% of delivered orders arrive late (on-time 91.87%).
- **Finding (regions):** Among states with at least 500 orders, on-time rates are lowest in MA (80.5%), CE (84.6%), BA (85.9%), RJ (86.5%) and PA (87.6%), compared with 94.1% in SP and 94.4% in MG. RJ matters most because it is the second-largest state: about 970 more late orders than it would have at MG's on-time rate *(derived, approximate)*. RJ also averages 15.2 delivery days vs 8.7 in SP.
- **Finding (over time):** On-time delivery fell to 85.7% in Nov 2017, 84.0% in Feb 2018 and 78.6% in Mar 2018, with review scores falling to 3.99, 3.88 and 3.81 in those months (typical months are 4.2 to 4.3). March 2018 had no volume spike (7,003 delivered vs 7,069 in Jan, when on-time was 93.4%), so volume alone does not explain it. *(Hypothesis: carrier or regional disruption; not provable from this data.)*
- **Recommendation:** (1) Review carriers and lanes serving RJ. (2) Investigate Feb-Mar 2018 and plan peak capacity before November. (3) In the remote north-east states (MA, CE, PA, averaging 21 to 24 days) consider more realistic delivery estimates, since reviews respond to lateness against the promised date; weigh this against possible effects on conversion.
- **Estimated impact and assumptions:** see Q6; fewer late orders is where the measurable benefit is.

## Q6. How much do late deliveries reduce review scores?
**Source:** `mart_delivery_impact`

| Delivery | Orders | Avg review | 1-2 star reviews |
|---|---|---|---|
| On time or early | 87,902 | 4.29 | 9.2% |
| 1-3 days late | 2,635 | 3.77 | 19.1% |
| 4-7 days late | 1,773 | 2.32 | 61.3% |
| 8-14 days late | 1,748 | 1.74 | 78.2% |
| 15+ days late | 1,502 | 1.71 | 78.8% |

- **Finding:** There is a cliff after 3 days: the average falls from 3.77 to 2.32. Late orders are 8.0% of reviewed deliveries but account for 33.9% of all 1-2 star reviews *(derived)*. Orders more than 3 days late number 5,023, or 5.3% of the total.
- **Recommendation:** Focus on the more-than-3-days-late group first. Trigger proactive customer contact or compensation when an order passes the estimated date by 2 days.
- **Estimated impact and assumptions:** If those 5,023 orders scored like on-time orders, the overall average review would rise from 4.16 to about 4.28 and 1-2 star reviews would fall by roughly 26% *(derived)*. This is an optimistic upper bound: it assumes lateness causes the score gap, whereas late orders may also differ in distance, product or seller.

## Q7. Which sellers underperform on delivery or reviews?
**Source:** `mart_seller_performance`

- **Finding:** 625 of 2,945 sellers have at least 30 orders and can be ranked; they generate 77.2% of revenue. The 10 lowest-rated rankable sellers average between 2.39 and 3.34 stars (marketplace 4.16), and 11% to 32% of their orders are late (marketplace 8.1%). Together they handled 809 orders and BRL 104.9K, which is 0.8% of revenue *(derived)*.
- **Finding:** Lateness does not explain everything. One seller with 187 orders is 13.9% late but averages 2.79 stars, which suggests product or service problems. *(Hypothesis.)*
- **Recommendation:** Open a performance review for these 10 sellers and extend the same screen to all rankable sellers under a chosen score threshold. Because they carry under 1% of revenue, acting has little commercial risk.
- **Estimated impact and assumptions:** the revenue at stake is small; the benefit is mainly reputational. Orders with several sellers are attributed to every seller involved, so treat the ranking as indicative.

## Q8. What will weekly demand be by category over the next 8 weeks?
**Source:** `forecast.weekly_forecast`, `docs/forecast_report.md`

- **Finding:** For the 15 largest categories the outlook is flat: about 1,546 units a week, 1.6% below the last-4-week average and 1.0% above the last week. The forecast is a statistical extrapolation of recent demand, with no knowledge of promotions or growth, and it starts from the week of 2018-08-20 because later data is incomplete.
- **Recommendation:** Plan with the 4-week moving average as the default and add a manual uplift for known peaks.
- **Estimated impact and assumptions:** none claimed. A per-category "change vs the last 8 weeks" figure in the forecast table is misleading, since those weeks include two unusually low weeks in early July.

## Q9. Which categories have the highest forecast uncertainty?
**Source:** `forecast.category_uncertainty`, `forecast.accuracy_summary`

- **Finding:** Typical error is about 26% to 29% of demand per category-week, roughly doubling from 1 to 8 weeks ahead. The hardest categories (holdout WAPE) are garden_tools (0.465), watches_gifts (0.428), office_furniture (0.372), computers_accessories (0.369) and cool_stuff (0.349); the easiest are bed_bath_table (0.154) and baby (0.200). No model beats a simple 4-week moving average, and all under-forecast the Black Friday spike by 52% to 58%.
- **Recommendation:** Carry more safety stock for the hard categories, plan peaks manually, and do not rely on LightGBM at this history length.
- **Estimated impact and assumptions:** none claimed. Error bands captured 71.7% of holdout actuals against a nominal 80%, so treat them as roughly 70% bands. The holdout is only 4 origins, so differences between the leading models are within noise.

## Q10. What is the estimated impact of improving on-time delivery?
**Source:** `mart_delivery_vs_repeat`

- **Finding:** Customers whose first delivery was late reordered within 180 days at 1.65% (75 of 4,534) versus 2.01% for on-time first deliveries (1,037 of 51,652). The gap is 0.35 percentage points, with a 95% confidence interval of about -0.04 to +0.74 points and p of about 0.10 *(derived)*. That is not statistically distinguishable from zero.
- **Finding:** The first-order review scores differ sharply (2.40 late vs 4.27 on time), so late deliveries clearly hurt satisfaction even though repeat purchasing barely moves.
- **Recommendation:** Justify delivery improvements by review quality and reputation, not by repeat revenue.
- **Estimated impact and assumptions:** Fixing every late first delivery would add about 27 repeat customers (about BRL 3.6K) if the whole gap were causal, about 13 if half; even the upper confidence bound gives about 56 customers (about BRL 7.7K) *(derived)*. This assumes eligible customers represent all customers and one extra order each at the average value. Revenue impact through repeat purchasing is negligible.

---

## Recommendations in priority order

| # | Action | Evidence | Expected effect |
|---|---|---|---|
| 1 | Prevent orders going more than 3 days late (alert at estimate + 2 days) | Q6 | Largest controllable lever on reviews; up to about +0.12 stars overall (upper bound) |
| 2 | Fix RJ delivery performance | Q5 | About 970 fewer late orders in the second-largest state |
| 3 | Review the weakest rankable sellers | Q7 | Cleaner marketplace; low commercial risk (0.8% of revenue) |
| 4 | Back faster-growing categories; investigate cool_stuff | Q1 | Guides inventory and marketing; about BRL 270K gap vs market rate |
| 5 | Plan peak-period capacity; investigate Feb-Mar 2018 | Q2, Q5 | Protects reviews during high-volume months |
| 6 | Test retention with a holdout group | Q3, Q4 | Modest (a doubled repeat rate is about 2.9% of revenue) |
| 7 | Plan weekly demand with a 4-week moving average, a manual peak uplift and category safety stock | Q8, Q9 | Simple and robust; avoids over-trusting a model that cannot beat it |

## Limitations to state in the README
- One marketplace, anonymised, Sep 2016 to Oct 2018; the analysis window is 20 months with one holiday season.
- Purchase capture thins out after about 2018-08-19, so August 2018 totals are understated. Monthly KPIs flag it (`is_complete_month = false`); the weekly demand table stops at the week ending Aug 19.
- Repeat purchasing is rare and right-censored: late-acquired customers have had less time to return.
- Delivery effects are associations, not proven causes; multi-seller orders count toward every seller.
- Average delivery days fall in Jun-Aug 2018 (9.2, 8.9, 7.7). Part of that may be because orders still in transit at the data cutoff are not counted, so do not read it as a real improvement.

## Still to check
- Notebook-only outputs not yet reviewed: day-of-week pattern, number of categories making up 80% of revenue, null-rate table from the EDA.
- The hypotheses marked above (Black Friday spike, causes of the RJ and Feb-Mar 2018 problems, seller quality issues).
