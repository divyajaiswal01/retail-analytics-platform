-- Category performance on delivered items in the analysis window.
-- Growth compares the yoy_current period with the same dates one year earlier
-- (same calendar months, so seasonality does not distort the comparison).
with items as (

    select
        dp.category_name_en as category,
        i.order_id,
        i.price,
        i.order_date
    from {{ ref('fact_order_items') }} as i
    inner join {{ ref('dim_product') }} as dp on i.product_key = dp.product_key
    where i.in_analysis_window
      and i.is_delivered

),

totals as (

    select
        category,
        count(*)                   as items_sold,
        count(distinct order_id)   as orders,
        sum(price)                 as revenue,
        round(avg(price), 2)       as avg_price
    from items
    group by category

),

periods as (

    select
        category,
        coalesce(sum(price) filter (
            where order_date between cast('{{ var("yoy_current_start") }}' as date)
                                 and cast('{{ var("yoy_current_end") }}' as date)
        ), 0) as revenue_current_period,
        coalesce(sum(price) filter (
            where order_date between cast(cast('{{ var("yoy_current_start") }}' as date) - interval 1 year as date)
                                 and cast(cast('{{ var("yoy_current_end") }}' as date) - interval 1 year as date)
        ), 0) as revenue_prior_period
    from items
    group by category

)

select
    rank() over (order by t.revenue desc, t.category)                        as revenue_rank,
    t.category,
    t.items_sold,
    t.orders,
    t.revenue,
    t.avg_price,
    round(100.0 * t.revenue / sum(t.revenue) over (), 2)                     as revenue_share_pct,
    round(
        100.0 * sum(t.revenue) over (order by t.revenue desc, t.category
                                     rows between unbounded preceding and current row)
        / sum(t.revenue) over (), 2
    )                                                                        as cumulative_share_pct,
    p.revenue_current_period,
    p.revenue_prior_period,
    case
        when p.revenue_prior_period > 0
        then round(100.0 * (p.revenue_current_period - p.revenue_prior_period) / p.revenue_prior_period, 2)
    end                                                                      as yoy_growth_pct
from totals as t
inner join periods as p on t.category = p.category
