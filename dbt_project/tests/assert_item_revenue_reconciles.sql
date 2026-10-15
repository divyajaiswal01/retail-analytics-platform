-- Total item revenue in fact_orders must equal the sum of staged item prices (no fan-out).
select f.total as fact_total, s.total as staging_total
from (select sum(items_revenue) as total from {{ ref('fact_orders') }}) as f
cross join (select sum(price) as total from {{ ref('stg_order_items') }}) as s
where abs(f.total - s.total) > 0.01
