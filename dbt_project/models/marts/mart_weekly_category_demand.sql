-- Weekly demand per category: the input to the forecasting module (Phase 6).
-- Demand = delivered items (units), by the Monday-start week of the order date.
--
-- Only COMPLETE weeks are kept: inside the analysis window AND on or before data_complete_through
-- (purchase capture thins out at the very end of the dataset). The window starts on a Sunday and
-- ends on a Friday, so the edge weeks are partial and would look like false demand drops.
-- Every category x week pair is present (zero-filled) so the series have no gaps.
with bounds as (

    -- first Monday on/after the window start; last Monday whose Sunday is still inside the window
    -- and inside the verified-complete data
    select
        cast(date_trunc('week', cast('{{ var("analysis_start_date") }}' as date) + 6) as date) as first_week,
        cast(
            date_trunc(
                'week',
                least(
                    cast('{{ var("analysis_end_date") }}' as date),
                    cast('{{ var("data_complete_through") }}' as date)
                ) - 6
            ) as date
        ) as last_week

),

weeks as (

    select cast(unnest(generate_series(first_week, last_week, interval 7 day)) as date) as week_start
    from bounds

),

items as (

    select
        dp.category_name_en              as category,
        d.week_start,
        i.order_id,
        i.price
    from {{ ref('fact_order_items') }} as i
    inner join {{ ref('dim_product') }} as dp on i.product_key = dp.product_key
    inner join {{ ref('dim_date') }} as d on i.order_date = d.date_day
    where i.is_delivered
      and i.in_analysis_window

),

categories as (

    select distinct category from items

),

weekly as (

    select
        category,
        week_start,
        count(*)                   as units,
        count(distinct order_id)   as orders,
        sum(price)                 as revenue
    from items
    group by category, week_start

)

select
    c.category || '|' || cast(w.week_start as varchar)       as demand_key,
    w.week_start,
    c.category,
    coalesce(k.units, 0)                                      as units,
    coalesce(k.orders, 0)                                     as orders,
    coalesce(k.revenue, 0)                                    as revenue,
    r.revenue_rank                                            as category_revenue_rank
from weeks as w
cross join categories as c
left join weekly as k
    on w.week_start = k.week_start
   and c.category = k.category
left join {{ ref('mart_category_performance') }} as r
    on c.category = r.category
