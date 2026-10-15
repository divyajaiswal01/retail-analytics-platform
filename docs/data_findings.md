# Data Findings & Decisions

**Source:** `analytics/notebooks/01_eda.ipynb` run on the real Olist dataset.
**Purpose:** record every data issue and the decision made, so dbt staging (Phase 4) is traceable to evidence.

> How to use: run the notebook, then fill the **Evidence** column with your real numbers.
> The **Proposed decision** column is a sensible default to confirm or change after you see the evidence.
> Do not keep a decision you can't justify with a number from your own run.

---

## 1. Dataset snapshot (fill from notebook sections 1 and 5)

| Item | Value |
|---|---|
| Tables loaded | |
| Total orders | |
| First order date | |
| Last order date | |
| Usable window chosen | |
| Reason for window | |

---

## 2. Issues & decisions

| # | Area | What to check (notebook section) | Evidence (your numbers) | Proposed decision | Implemented in |
|---|---|---|---|---|---|
| 1 | Customer identity | `customer_id` vs `customer_unique_id` uniqueness (3) | | Use `customer_unique_id` as the true customer key for repeat rate, RFM, and cohorts | `dim_customer` |
| 2 | Sparse months | Orders per month at start/end of data (5) | | Restrict analysis and forecasting to months above a minimum order volume | `dim_date`, forecast mart |
| 3 | Order status | Share of non-delivered statuses (6) | | Count revenue only for `delivered` orders; keep other statuses in the fact table with a flag | `fact_orders` |
| 4 | Delivered, no date | `delivered_missing_date` (7) | | Exclude from on-time % and delivery-days metrics; keep in revenue | `fact_orders` |
| 5 | Impossible dates | `delivered_before_purchase` (7) | | Set delivery metrics to NULL and flag the row | `stg_orders` |
| 6 | Multiple payments | Payments per order (8) | | Aggregate payments to one row per order before joining | `fact_orders` |
| 7 | Orders without items | `orders_without_items` by status (8) | | Keep in `fact_orders`; exclude from item-level analysis | `fact_orders` |
| 8 | Payment mismatch | Item total vs payment total (8) | | Use item price as the revenue measure; report payment mismatches as a quality note | `fact_orders` |
| 9 | Multiple reviews | Reviews per order (9) | | Keep one review per order (the most recent by answer timestamp) | `stg_reviews` |
| 10 | Missing category | `no_category` (10) | | Map to `unknown` category rather than dropping products | `dim_product` |
| 11 | Untranslated categories | Categories with no English name (10) | | Add manual translations or fall back to the Portuguese name | `dim_product` |
| 12 | Zero/NULL weights | `weight_zero`, `weight_missing` (10) | | Treat as NULL; do not impute for now | `stg_products` |
| 13 | Price/freight outliers | Zero/negative values and p99 vs max (11) | | Keep values; flag extreme outliers; never silently delete | `stg_order_items` |
| 14 | Orphan keys | Orphan counts (4) | | Keep rows; use LEFT JOINs; assign unknown member where a dimension is missing | marts |
| 15 | Geolocation grain | Rows per zip prefix (12) | | Reduce to one row per zip prefix (average lat/lng) before joining | `stg_geolocation` |

Add new rows below as you discover more issues.

---

## 3. Data quality notes for the README

Short list of known limitations to state honestly in the final documentation (e.g. date coverage, anonymized data, BRL currency, any dropped or flagged records).

-
-
-

---



## 4. Open questions

Anything that needs a decision before Phase 4:

-
RESULTS 
=== 1. ROW COUNTS ===
               table    rows
           customers   99441
         geolocation 1000163
         order_items  112650
      order_payments  103886
       order_reviews   99224
              orders   99441
            products   32951
             sellers    3095
category_translation      71

=== 3. KEY UNIQUENESS ===
               table                          key   rows  distinct_keys  duplicate_rows
           customers                  customer_id  99441          99441               0
           customers           customer_unique_id  99441          96096            3345
              orders                     order_id  99441          99441               0
         order_items      order_id, order_item_id 112650         112650               0
      order_payments order_id, payment_sequential 103886         103886               0
       order_reviews                    review_id  99224          98410             814
       order_reviews                     order_id  99224          98673             551
            products                   product_id  32951          32951               0
             sellers                    seller_id   3095           3095               0
category_translation        product_category_name     71             71               0

=== 4. ORPHANS ===
                         child                                     parent  orphan_rows
            orders.customer_id                      customers.customer_id            0
          order_items.order_id                            orders.order_id            0
        order_items.product_id                        products.product_id            0
         order_items.seller_id                          sellers.seller_id            0
       order_payments.order_id                            orders.order_id            0
        order_reviews.order_id                            orders.order_id            0
products.product_category_name category_translation.product_category_name           13

=== 5. MONTHLY ORDERS ===
  month  orders  delivered_orders
2016-09       4                 1
2016-10     324               265
2016-12       1                 1
2017-01     800               750
2017-02    1780              1653
2017-03    2682              2546
2017-04    2404              2303
2017-05    3700              3546
2017-06    3245              3135
2017-07    4026              3872
2017-08    4331              4193
2017-09    4285              4150
2017-10    4631              4478
2017-11    7544              7289
2017-12    5673              5513
2018-01    7269              7069
2018-02    6728              6555
2018-03    7211              7003
2018-04    6939              6798
2018-05    6873              6749
2018-06    6167              6099
2018-07    6292              6159
2018-08    6512              6351
2018-09      16                 0
2018-10       4                 0

=== 6. ORDER STATUS ===
order_status  orders   pct
   delivered   96478 97.02
     shipped    1107  1.11
    canceled     625  0.63
 unavailable     609  0.61
    invoiced     314  0.32
  processing     301  0.30
     created       5  0.01
    approved       2  0.00

=== 7. DELIVERY LOGIC ===
                    metric     value
          delivered_orders 96,478.00
    delivered_missing_date      8.00
not_delivered_but_has_date      6.00
 delivered_before_purchase      0.00
               late_orders  7,826.00
                  late_pct      8.11

=== 8. COVERAGE ===
 orders  orders_without_items  orders_without_payments  orders_without_reviews
  99441                   775                        1                     768

=== 8. PAYMENTS PER ORDER ===
 payments_per_order  orders
                  1   96479
                  2    2382
                  3     301
                  4     108
                  5      52
                  6      36
                  7      28
                  8      11
                  9       9
                 10       5
                 11       8
                 12       8
                 13       3
                 14       2
                 15       2
                 19       2
                 21       1
                 22       1
                 26       1
                 29       1

=== 8. PAYMENT RECONCILIATION ===
 orders_compared  mismatches_over_tolerance  mismatch_pct
           98665                        249          0.25

=== 9. REVIEWS PER ORDER ===
 reviews_per_order  orders
                 1   98126
                 2     543
                 3       4

=== 10. PRODUCTS ===
 products  no_category  weight_missing  weight_zero
    32951          610               2            4

=== 10. UNTRANSLATED CATEGORIES ===
                                     category  products
portateis_cozinha_e_preparadores_de_alimentos        10
                                     pc_gamer         3

=== 11. OUTLIERS ===
                       field      n  unparseable  zero_or_negative  min    p50       p99       max
           order_items.price 112650            0                 0 0.85  74.99    890.00  6,735.00
   order_items.freight_value 112650            0               383 0.00  16.26     84.52    409.68
order_payments.payment_value 103886            0                 9 0.00 100.00  1,039.92 13,664.08
   products.product_weight_g  32951            2                 4 0.00 700.00 22,538.00 40,425.00

=== 12. GEOLOCATION ===
   rows  distinct_zips
1000163          19015
