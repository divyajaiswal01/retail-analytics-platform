-- Sales cube for dashboard drill-down: delivered items by purchase month, category and customer state.
-- Only ADDITIVE measures (items, revenue) are kept so any filter combination can be summed correctly.
-- (Order counts are not additive across categories, so they are deliberately not included.)
with items as (

    select
        d.year_month,
        dp.category_name_en           as category,
        coalesce(c.state, 'unknown')  as state,
        i.price
    from {{ ref('fact_order_items') }} as i
    inner join {{ ref('dim_date') }} as d on i.order_date = d.date_day
    inner join {{ ref('dim_product') }} as dp on i.product_key = dp.product_key
    inner join {{ ref('fact_orders') }} as o on i.order_id = o.order_id
    inner join {{ ref('dim_customer') }} as c on o.customer_key = c.customer_key
    where i.in_analysis_window
      and i.is_delivered

),

month_bounds as (

    select year_month, max(date_day) as month_end
    from {{ ref('dim_date') }}
    group by year_month

),

cube as (

    select
        year_month,
        category,
        state,
        count(*)     as items_sold,
        sum(price)   as revenue
    from items
    group by year_month, category, state

)

select
    cube.year_month || '|' || cube.category || '|' || cube.state                 as cube_key,
    cube.year_month,
    cube.category,
    cube.state,
    cube.items_sold,
    cube.revenue,
    month_bounds.month_end <= cast('{{ var("data_complete_through") }}' as date) as is_complete_month
from cube
inner join month_bounds on cube.year_month = month_bounds.year_month
