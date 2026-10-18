select b.n as bucket_orders, f.n as fact_orders
from (select sum(orders) as n from {{ ref('mart_delivery_impact') }}) as b
cross join (
    select count(*) as n from {{ ref('fact_orders') }}
    where in_analysis_window and is_delivered and is_late is not null and review_score is not null
) as f
where b.n <> f.n
