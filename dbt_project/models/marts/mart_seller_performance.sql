-- Seller performance on delivered orders in the analysis window.
-- An order with several sellers is attributed to each of them (lateness and review included).
-- Sellers under seller_min_orders are flagged meets_min_volume = false: too few orders to rank.
with seller_orders as (

    select
        seller_key,
        order_id,
        sum(price) as seller_revenue
    from {{ ref('fact_order_items') }}
    where in_analysis_window
      and is_delivered
    group by seller_key, order_id

),

joined as (

    select
        so.seller_key,
        so.order_id,
        so.seller_revenue,
        f.is_late,
        f.delivery_days,
        f.review_score
    from seller_orders as so
    inner join {{ ref('fact_orders') }} as f on so.order_id = f.order_id

),

overall as (

    select
        round(100.0 * count(*) filter (where is_late) / nullif(count(*) filter (where is_late is not null), 0), 2) as overall_late_pct,
        round(avg(review_score), 3) as overall_avg_review_score
    from {{ ref('fact_orders') }}
    where in_analysis_window
      and is_delivered

),

sellers as (

    select
        seller_key,
        count(*)                                                               as orders,
        sum(seller_revenue)                                                    as revenue,
        round(100.0 * count(*) filter (where is_late)
              / nullif(count(*) filter (where is_late is not null), 0), 2)     as late_pct,
        round(avg(delivery_days), 1)                                           as avg_delivery_days,
        round(avg(review_score), 3)                                            as avg_review_score,
        count(review_score)                                                    as reviewed_orders
    from joined
    group by seller_key

)

select
    s.seller_key,
    d.state,
    s.orders,
    s.revenue,
    s.late_pct,
    s.avg_delivery_days,
    s.avg_review_score,
    s.reviewed_orders,
    s.orders >= {{ var("seller_min_orders") }}                                 as meets_min_volume,
    o.overall_late_pct,
    o.overall_avg_review_score
from sellers as s
left join {{ ref('dim_seller') }} as d on s.seller_key = d.seller_key
cross join overall as o
