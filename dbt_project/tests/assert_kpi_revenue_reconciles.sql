-- Monthly KPI revenue must equal delivered revenue in fact_orders for the window.
select m.total as kpi_total, f.total as fact_total
from (select sum(delivered_revenue) as total from {{ ref('metrics_kpis') }}) as m
cross join (
    select sum(delivered_revenue) as total from {{ ref('fact_orders') }} where in_analysis_window
) as f
where abs(m.total - f.total) > 0.01
