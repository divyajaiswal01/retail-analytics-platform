-- The cube must add up to delivered revenue and delivered items for the window (nothing lost or doubled).
select c.revenue as cube_revenue, f.revenue as fact_revenue, c.items as cube_items, f.items as fact_items
from (select sum(revenue) as revenue, sum(items_sold) as items from {{ ref('mart_sales_cube') }}) as c
cross join (
    select
        (select sum(delivered_revenue) from {{ ref('fact_orders') }} where in_analysis_window) as revenue,
        (select count(*) from {{ ref('fact_order_items') }} where in_analysis_window and is_delivered) as items
) as f
where abs(c.revenue - f.revenue) > 0.01
   or c.items <> f.items
