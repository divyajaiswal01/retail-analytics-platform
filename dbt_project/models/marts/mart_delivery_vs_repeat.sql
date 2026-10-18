-- Does a late FIRST delivery reduce the chance a customer orders again within the horizon?
-- Eligible customers: first-ever delivered order inside the window, with a known on-time/late
-- status, and at least repeat_horizon_days of follow-up before the window ends (so every
-- customer has the same observation time). Association only; not proof of causation.
with delivered as (

    select customer_key, order_id, order_date, is_late, review_score
    from {{ ref('fact_orders') }}
    where is_delivered
      and order_date <= cast('{{ var("analysis_end_date") }}' as date)

),

ranked as (

    select
        customer_key,
        order_date,
        is_late,
        review_score,
        row_number() over (partition by customer_key order by order_date, order_id) as order_rank
    from delivered

),

first_orders as (

    select
        customer_key,
        order_date   as first_order_date,
        is_late      as first_order_late,
        review_score as first_review_score
    from ranked
    where order_rank = 1

),

eligible as (

    select *
    from first_orders
    where first_order_date between cast('{{ var("analysis_start_date") }}' as date)
                               and cast('{{ var("analysis_end_date") }}' as date)
      and first_order_date + {{ var("repeat_horizon_days") }} <= cast('{{ var("analysis_end_date") }}' as date)
      and first_order_late is not null

),

repeaters as (

    select distinct d.customer_key
    from delivered as d
    inner join first_orders as f on d.customer_key = f.customer_key
    where d.order_date > f.first_order_date
      and d.order_date <= f.first_order_date + {{ var("repeat_horizon_days") }}

)

select
    case when e.first_order_late then 'late' else 'on time or early' end   as first_delivery,
    count(*)                                                               as customers,
    count(r.customer_key)                                                  as repeat_customers,
    round(100.0 * count(r.customer_key) / count(*), 3)                     as repeat_rate_pct,
    round(avg(e.first_review_score), 3)                                    as avg_first_review_score
from eligible as e
left join repeaters as r on e.customer_key = r.customer_key
group by e.first_order_late
