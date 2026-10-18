select s.total as seller_total, f.total as fact_total
from (select sum(revenue) as total from {{ ref('mart_seller_performance') }}) as s
cross join (
    select sum(price) as total from {{ ref('fact_order_items') }}
    where in_analysis_window and is_delivered
) as f
where abs(s.total - f.total) > 0.01
