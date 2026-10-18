-- Regional performance by customer state (delivered orders in the analysis window).
select
    c.state,
    count(distinct f.customer_key)                                            as customers,
    count(*)                                                                  as delivered_orders,
    sum(f.delivered_revenue)                                                  as delivered_revenue,
    round(sum(f.delivered_revenue) / nullif(count(*) filter (where f.delivered_revenue > 0), 0), 2) as aov,
    round(100.0 * sum(f.delivered_revenue) / sum(sum(f.delivered_revenue)) over (), 2) as revenue_share_pct,
    round(100.0 * count(*) filter (where f.is_late = false)
          / nullif(count(*) filter (where f.is_late is not null), 0), 2)      as on_time_pct,
    round(avg(f.delivery_days), 1)                                            as avg_delivery_days,
    round(avg(f.review_score), 3)                                             as avg_review_score
from {{ ref('fact_orders') }} as f
inner join {{ ref('dim_customer') }} as c on f.customer_key = c.customer_key
where f.in_analysis_window
  and f.is_delivered
group by c.state
