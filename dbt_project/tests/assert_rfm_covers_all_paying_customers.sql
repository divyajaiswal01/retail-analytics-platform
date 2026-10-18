select r.n as rfm_customers, f.n as fact_customers
from (select count(*) as n from {{ ref('mart_customer_rfm') }}) as r
cross join (
    select count(distinct customer_key) as n
    from {{ ref('fact_orders') }}
    where in_analysis_window and is_delivered and delivered_revenue > 0
) as f
where r.n <> f.n
