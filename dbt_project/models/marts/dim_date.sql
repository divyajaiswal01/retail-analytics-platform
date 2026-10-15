-- One row per calendar day from the first purchase to the last delivery/estimate date.
with bounds as (

    select
        cast(min(purchased_at) as date) as start_date,
        cast(greatest(max(purchased_at), max(delivered_at), max(estimated_delivery_at)) as date) as end_date
    from {{ ref('stg_orders') }}

),

spine as (

    select cast(unnest(generate_series(start_date, end_date, interval 1 day)) as date) as date_day
    from bounds

)

select
    date_day,
    extract(year from date_day)                       as year,
    extract(quarter from date_day)                    as quarter,
    extract(month from date_day)                      as month,
    strftime(date_day, '%Y-%m')                       as year_month,
    monthname(date_day)                               as month_name,
    cast(date_trunc('week', date_day) as date)        as week_start,
    isodow(date_day)                                  as day_of_week,
    dayname(date_day)                                 as day_name,
    isodow(date_day) in (6, 7)                        as is_weekend
from spine
