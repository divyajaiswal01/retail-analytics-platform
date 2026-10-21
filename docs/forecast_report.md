# Demand Forecast Report

**Window:** weekly demand for the 15 largest categories, 2017-01-02 to 2018-08-13 (85 weeks).
**Status:** results from the real warehouse. Figures are WAPE (total absolute error / total actual units; lower is better) unless stated.

## Summary
- **No model clearly beats a simple 4-week moving average.** On the holdout it scored 0.260; the selected policy scored 0.286, ETS 0.291, naive 0.293 and LightGBM 0.356.
- **Typical error is about 26% to 29% of actual demand per category-week.** For the selected policy it roughly doubles from 1 week ahead (0.18) to 8 weeks ahead (0.36).
- **Every model misses a holiday spike badly:** in the Black Friday weeks all of them under-forecast by 52% to 58%.
- **The outlook for the next 8 weeks is flat:** about 1,546 units a week across the 15 categories, close to the recent level (about 1,571 over the last 4 weeks).
- **The evidence is thin.** The holdout has 4 origins with overlapping 8-week targets, so differences of a few percent between the leading models are within noise.

## 1. What is forecast
- **Target:** weekly delivered units per product category (Monday-start weeks).
- **Scope:** the 15 largest categories by revenue. Product-level data is too sparse to forecast reliably.
- **Horizon:** 8 weeks ahead. **History:** 85 complete weeks.
- **History ends 2018-08-13** because purchases are not fully captured after 2018-08-19 (daily items fall from about 290 to 16 by Aug 29; see `docs/data_findings.md` finding #16). The forecast therefore starts from the week of 2018-08-20 and cannot be checked against real data.
- **Demand definition:** delivered items. Checked: in the final weeks only 0.3% to 1.5% of items were still in progress, so delivery lag does not understate recent demand.

## 2. Method
| Model | Role | Notes |
|---|---|---|
| Naive | baseline | repeats the latest week |
| Moving average (4 weeks) | baseline | repeats the 4-week mean |
| Seasonal naive (52 weeks) | reference only | needs a full year of history |
| ETS (damped trend) | candidate | one fit per category, no seasonality |
| LightGBM | candidate | one global model per horizon; features scaled by each category's recent level |

- **Validation:** walk-forward backtest with 12 origins spaced 4 weeks apart, each trained only on weeks up to the origin. A counterfactual test confirms that rewriting future weeks never changes a forecast.
- **Model choice:** one candidate (ETS, WAPE 0.301 vs 0.346 for LightGBM on the 8 earliest origins) is used for a category only if it beats that category's best baseline by 5%; otherwise the category falls back to the baseline. Result: ETS for 3 categories (bed_bath_table, baby, office_furniture), naive for 10, moving average for 2 (cool_stuff, telephony). The latest 4 origins were never used for choosing, so they are an honest test.

## 3. Results
**Holdout (4 latest origins, 480 forecasts):**

| Model | WAPE | Bias | vs 4-week average |
|---|---|---|---|
| Moving average (4 weeks) | 0.260 | +7.0% | best |
| **Selected policy** | 0.286 | +5.1% | +10% worse |
| ETS | 0.291 | +8.6% | +12% worse |
| Naive | 0.293 | +1.3% | +13% worse |
| LightGBM | 0.356 | +20.6% | +37% worse |
| Seasonal naive (52 weeks) | 0.560 | -51.5% | +115% worse |

- **Across all 12 origins** the picture is different: ETS 0.297, naive 0.299, moving average 0.308, LightGBM 0.349. The top three are only about 4% apart, so none can be called the winner. LightGBM is consistently the weakest and over-forecasts, a sign that a flexible model overfits this short history.
- **Seasonal naive** fails because last year's level was far lower than this year's (about -52% to -59% bias). That confirms yearly seasonality cannot be used with this history.
- **The selected policy did not beat the best single baseline** (0.286 vs 0.260). Choosing a model separately per category on 8 origins fits noise: the policy picked naive for 10 categories because it narrowly led on the early origins, but the moving average did better on the later ones.
- **Error by horizon (holdout):** about 0.18 to 0.20 at 1 week and 0.17 to 0.22 at 2 weeks. From week 3 onward the baselines and ETS range from about 0.27 to 0.37, and LightGBM from 0.37 to 0.48. The pattern is uneven because only 4 origins are available.

## 4. The holiday spike
- In the Black Friday weeks every model under-forecasts: WAPE 0.53 to 0.59 and bias -52% to -58% (naive best at 0.531, moving average worst at 0.588, because it lags most).
- Only one holiday season is in the data, so no model can learn it.
- **Recommendation:** plan a peak as an event with a manual uplift. The only evidence available is Nov 2017, when delivered orders were about 63% above October and revenue 52% above (monthly figures). One observation is not enough to set a rule; revisit when a second season exists.

## 5. Uncertainty (Q9)
- **Error bands** use the 10th to 90th percentile of backtest errors per category. Built from the early origins and tested on the holdout, they captured **71.7%** of actuals against a nominal 80%, so treat them as roughly 70% bands.
- **Hardest to forecast (holdout WAPE):** garden_tools 0.465, watches_gifts 0.428, office_furniture 0.372, computers_accessories 0.369, cool_stuff 0.349.
- **Easiest:** bed_bath_table 0.154, baby 0.200, toys 0.206, telephony 0.243, housewares 0.246.
- **Two different views of risk.** Holdout WAPE reflects the calm 2018 period; the band width also includes the holiday spike. That is why toys has a low holdout error but the widest band.
- **Total band caveat:** the weekly totals for all categories (about 1,038 to 2,500 around 1,544) add up the per-category bands, which overstates the uncertainty of the total because category errors partly cancel.
- **Use:** carry more safety stock for the high-error categories and plan more tightly for bed_bath_table and baby.

## 6. Outlook for the next 8 weeks (Q8)
- **Total forecast:** about 1,544 to 1,548 units a week for the 15 categories (12,366 over 8 weeks).
- **Against recent demand:** 1.6% below the last-4-week average (1,571) and 1.0% above the last week (1,530).
- **Do not read the per-category "change vs last period" as growth.** It compares against the last 8 weeks, which contain two unusually low weeks (Jul 2 and Jul 9: 1,055 and 808 units). Against the last 4 weeks the outlook is flat.
- This is a statistical extrapolation of recent demand with no knowledge of promotions, events or growth trends. Flat forecasts are what these models produce by construction.

## 7. Recommendations
1. **Use the 4-week moving average as the default weekly planning forecast.** It is simple, was best on the holdout and in the full-year origins, and is not thrown off by one odd week. This is a judgement made after seeing the holdout, so confirm it as more data arrives.
2. **Do not deploy LightGBM** for this problem at the current history length.
3. **Add a manual uplift for known peaks** instead of trusting any model there.
4. **Set safety stock by category risk,** using the uncertainty ranking.
5. **Monitor rolling forecast error against the moving-average baseline** and alert when the model is worse (Phase 8).

## 8. Limitations
- Only 85 weeks of history and one holiday season; the holdout is 4 origins with overlapping targets, so small differences between models are not reliable.
- Weeks of 2018-07-02 and 2018-07-09 show unexplained dips in the top-15 total (1,055 and 808 units versus 1,244 to 1,305 in the three preceding weeks, roughly -17% and -37%), with normal delivery rates. They fall inside the holdout targets and raise every model's error. It is not known whether they are real demand or data gaps like the one at the end of August; checking daily counts for those weeks is an open item.
- The holdout is a calm 2018 period, so spike behaviour is judged only on the earlier peak slice.
- Small categories have noisy near-zero weeks, so percentage errors there are large.
- The selected policy's choices (naive for 10 categories) are fragile: they rest on 8 origins.
- Forecasts use delivered units and ignore a small share of demand that was cancelled.

## 9. Next steps
- Check the early-July dips with daily counts, and decide whether they should be treated as data gaps.
- Surface the forecast, bands and the moving-average baseline in the dashboard (Phase 7).
- Add rolling error monitoring and drift alerts (Phase 8).
- Revisit model choice and peak handling once a second holiday season is available.
