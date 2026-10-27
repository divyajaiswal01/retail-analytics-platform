-- One row: headline KPIs for the whole analysis window (delivered orders only).
-- Repeat rate = customers with 2+ delivered orders in the window / customers with 1+.
with base as (

    select
        customer_key,
        delivered_revenue,
        is_late,
        delivery_days,
        review_score
    from {{ ref('fact_orders') }}
    where in_analysis_window
      and is_delivered

),

customers as (

    select customer_key, count(*) as delivered_orders
    from base
    group by customer_key

)

select
    cast('{{ var("analysis_start_date") }}' as date)                       as window_start,
    cast('{{ var("analysis_end_date") }}' as date)                         as window_end,
    cast('{{ var("data_complete_through") }}' as date)                     as data_complete_through,
    (select count(*) from base)                                            as delivered_orders,
    (select sum(delivered_revenue) from base)                              as delivered_revenue,
    round(
        (select sum(delivered_revenue) from base)
        / nullif((select count(*) from base where delivered_revenue > 0), 0), 2
    )                                                                      as aov,
    (select count(*) from customers)                                       as customers,
    (select count(*) from customers where delivered_orders >= 2)           as repeat_customers,
    round(
        100.0 * (select count(*) from customers where delivered_orders >= 2)
        / nullif((select count(*) from customers), 0), 2
    )                                                                      as repeat_rate_pct,
    round(
        100.0 * (select count(*) from base where is_late = false)
        / nullif((select count(*) from base where is_late is not null), 0), 2
    )                                                                      as on_time_pct,
    round((select avg(delivery_days) from base), 1)                        as avg_delivery_days,
    round((select avg(review_score) from base), 3)                         as avg_review_score
