-- Category revenue must add up to total delivered revenue (no lost or doubled items).
select c.total as category_total, f.total as fact_total
from (select sum(revenue) as total from {{ ref('mart_category_performance') }}) as c
cross join (
    select sum(delivered_revenue) as total from {{ ref('fact_orders') }} where in_analysis_window
) as f
where abs(c.total - f.total) > 0.01
