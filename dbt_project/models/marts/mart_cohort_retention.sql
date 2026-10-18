-- Cohort retention: customers grouped by the month of their FIRST delivered order (all time),
-- keeping only cohorts that start inside the analysis window. For each month since the first
-- order, the share of the cohort that ordered again that month. Month 0 is always 100%.
with delivered as (

    select
        customer_key,
        cast(date_trunc('month', order_date) as date) as order_month
    from {{ ref('fact_orders') }}
    where is_delivered
      and order_date <= cast('{{ var("analysis_end_date") }}' as date)

),

first_order as (

    select customer_key, min(order_month) as cohort_month
    from delivered
    group by customer_key

),

cohort_sizes as (

    select cohort_month, count(*) as cohort_size
    from first_order
    where cohort_month >= cast(date_trunc('month', cast('{{ var("analysis_start_date") }}' as date)) as date)
    group by cohort_month

),

activity as (

    select
        f.cohort_month,
        date_diff('month', f.cohort_month, d.order_month) as months_since_first,
        count(distinct d.customer_key)                    as active_customers
    from delivered as d
    inner join first_order as f on d.customer_key = f.customer_key
    inner join cohort_sizes as s on f.cohort_month = s.cohort_month
    group by f.cohort_month, date_diff('month', f.cohort_month, d.order_month)

),

offsets as (

    select unnest(generate_series(0, 60)) as months_since_first

),

spine as (

    select s.cohort_month, s.cohort_size, o.months_since_first
    from cohort_sizes as s
    cross join offsets as o
    where s.cohort_month + to_months(cast(o.months_since_first as integer))
          <= cast(date_trunc('month', cast('{{ var("analysis_end_date") }}' as date)) as date)

)

select
    sp.cohort_month,
    sp.months_since_first,
    sp.cohort_size,
    coalesce(a.active_customers, 0)                                         as active_customers,
    round(100.0 * coalesce(a.active_customers, 0) / sp.cohort_size, 2)      as retention_pct
from spine as sp
left join activity as a
    on sp.cohort_month = a.cohort_month
   and sp.months_since_first = a.months_since_first
