select s.total as state_total, f.total as fact_total
from (select sum(delivered_revenue) as total from {{ ref('mart_state_performance') }}) as s
cross join (
    select sum(delivered_revenue) as total from {{ ref('fact_orders') }} where in_analysis_window
) as f
where abs(s.total - f.total) > 0.01
