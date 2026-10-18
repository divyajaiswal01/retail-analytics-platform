-- How delivery lateness relates to review scores (delivered, reviewed orders in the window).
-- This shows association, not proof of causation.
with base as (

    select
        order_id,
        review_score,
        delivery_days,
        is_late,
        case
            when is_late
            then cast(ceil((epoch(delivered_at) - epoch(estimated_delivery_at)) / 86400.0) as integer)
        end as days_late
    from {{ ref('fact_orders') }}
    where in_analysis_window
      and is_delivered
      and is_late is not null
      and review_score is not null

),

bucketed as (

    select
        order_id,
        review_score,
        delivery_days,
        case
            when not is_late then 1
            when days_late <= 3 then 2
            when days_late <= 7 then 3
            when days_late <= 14 then 4
            else 5
        end as bucket_order,
        case
            when not is_late then 'on time or early'
            when days_late <= 3 then '1-3 days late'
            when days_late <= 7 then '4-7 days late'
            when days_late <= 14 then '8-14 days late'
            else '15+ days late'
        end as delivery_bucket
    from base

)

select
    bucket_order,
    delivery_bucket,
    count(*)                                                                  as orders,
    round(avg(review_score), 3)                                               as avg_review_score,
    round(100.0 * count(*) filter (where review_score <= 2) / count(*), 2)    as pct_low_reviews,
    round(100.0 * count(*) filter (where review_score = 5) / count(*), 2)     as pct_five_star,
    round(avg(delivery_days), 1)                                              as avg_delivery_days
from bucketed
group by bucket_order, delivery_bucket
