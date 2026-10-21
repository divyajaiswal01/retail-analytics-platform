-- Monthly KPIs for the analysis window (one row per purchase month).
-- Revenue, AOV and delivery metrics use delivered orders only; orders_placed counts every status.
with first_delivered as (

    select
        customer_key,
        strftime(min(order_date), '%Y-%m') as first_delivered_month
    from {{ ref('fact_orders') }}
    where is_delivered
    group by customer_key

),

placed as (

    select
        d.year_month,
        count(*) as orders_placed
    from {{ ref('fact_orders') }} as f
    inner join {{ ref('dim_date') }} as d on f.order_date = d.date_day
    where f.in_analysis_window
    group by d.year_month

),

delivered as (

    select
        d.year_month,
        count(*)                                                       as delivered_orders,
        count(*) filter (where f.delivered_revenue > 0)                as revenue_orders,
        sum(f.delivered_revenue)                                       as delivered_revenue,
        sum(f.freight_total)                                           as freight_total,
        count(distinct f.customer_key)                                 as unique_customers,
        count(distinct f.customer_key)
            filter (where fd.first_delivered_month = d.year_month)     as new_customers,
        count(*) filter (where f.is_late = false)                      as on_time_orders,
        count(*) filter (where f.is_late is not null)                  as orders_with_delivery_date,
        avg(f.delivery_days)                                           as avg_delivery_days,
        avg(f.review_score)                                            as avg_review_score
    from {{ ref('fact_orders') }} as f
    inner join {{ ref('dim_date') }} as d on f.order_date = d.date_day
    inner join first_delivered as fd on f.customer_key = fd.customer_key
    where f.in_analysis_window
      and f.is_delivered
    group by d.year_month

),

month_bounds as (

    select year_month, max(date_day) as month_end
    from {{ ref('dim_date') }}
    group by year_month

),

monthly as (

    select
        p.year_month,
        p.orders_placed,
        coalesce(dl.delivered_orders, 0)                                as delivered_orders,
        coalesce(dl.delivered_revenue, 0)                               as delivered_revenue,
        round(dl.delivered_revenue / nullif(dl.revenue_orders, 0), 2)   as aov,
        coalesce(dl.freight_total, 0)                                   as freight_total,
        coalesce(dl.unique_customers, 0)                                as unique_customers,
        coalesce(dl.new_customers, 0)                                   as new_customers,
        coalesce(dl.unique_customers, 0) - coalesce(dl.new_customers, 0) as returning_customers,
        round(100.0 * dl.on_time_orders / nullif(dl.orders_with_delivery_date, 0), 2) as on_time_pct,
        round(dl.avg_delivery_days, 1)                                  as avg_delivery_days,
        round(dl.avg_review_score, 3)                                   as avg_review_score
    from placed as p
    left join delivered as dl on p.year_month = dl.year_month

)

select
    year_month,
    orders_placed,
    delivered_orders,
    delivered_revenue,
    aov,
    freight_total,
    unique_customers,
    new_customers,
    returning_customers,
    on_time_pct,
    avg_delivery_days,
    avg_review_score,
    round(
        100.0 * (delivered_revenue - lag(delivered_revenue) over (order by year_month))
        / nullif(lag(delivered_revenue) over (order by year_month), 0),
        2
    ) as revenue_mom_growth_pct,
    -- False when the month extends beyond data_complete_through: its totals are understated
    month_bounds.month_end <= cast('{{ var("data_complete_through") }}' as date) as is_complete_month
from monthly
inner join month_bounds using (year_month)
