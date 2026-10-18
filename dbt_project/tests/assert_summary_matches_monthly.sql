-- The one-row summary must agree with the monthly KPIs.
select s.delivered_orders as summary_orders, m.delivered_orders as monthly_orders
from {{ ref('metrics_summary') }} as s
cross join (select sum(delivered_orders) as delivered_orders from {{ ref('metrics_kpis') }}) as m
where s.delivered_orders <> m.delivered_orders
   or abs(s.delivered_revenue - (select sum(delivered_revenue) from {{ ref('metrics_kpis') }})) > 0.01
