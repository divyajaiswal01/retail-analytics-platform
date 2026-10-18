-- One row per customer with at least one delivered, paid order in the analysis window.
-- Recency is measured at the day after the window ends. Scores use cume_dist so tied values
-- always get the same score (ntile would split ties arbitrarily).
-- Frequency is bucketed 1 / 2 / 3+ because ~97% of customers order only once.
with orders as (

    select customer_key, order_date, delivered_revenue
    from {{ ref('fact_orders') }}
    where in_analysis_window
      and is_delivered
      and delivered_revenue > 0

),

rfm_base as (

    select
        customer_key,
        max(order_date)                                                              as last_order_date,
        date_diff('day', max(order_date), cast('{{ var("analysis_end_date") }}' as date) + 1) as recency_days,
        count(*)                                                                     as frequency,
        sum(delivered_revenue)                                                       as monetary
    from orders
    group by customer_key

),

scored as (

    select
        customer_key,
        last_order_date,
        recency_days,
        frequency,
        monetary,
        cast(ceil(5 * cume_dist() over (order by recency_days desc)) as integer) as r_score,
        case when frequency = 1 then 1 when frequency = 2 then 2 else 3 end       as f_score,
        cast(ceil(5 * cume_dist() over (order by monetary asc)) as integer)       as m_score
    from rfm_base

)

select
    customer_key,
    last_order_date,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    case
        when f_score >= 2 and r_score >= 3 then 'Repeat - active'
        when f_score >= 2 then 'Repeat - lapsed'
        when r_score >= 4 and m_score >= 4 then 'Recent high-value'
        when r_score >= 4 then 'Recent'
        when r_score = 3 then 'One-time - mid'
        when m_score >= 4 then 'Lapsed high-value'
        else 'Lapsed'
    end as segment
from scored
