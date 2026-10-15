-- One row per order (grain). Items, payments and reviews are aggregated to order level
-- BEFORE joining so no measure is double counted (findings #6, #8, #9).
with orders as (

    select
        order_id,
        customer_id,
        order_status,
        purchased_at,
        delivered_at,
        estimated_delivery_at
    from {{ ref('stg_orders') }}

),

customers as (

    select customer_id, customer_unique_id
    from {{ ref('stg_customers') }}

),

items as (

    select
        order_id,
        count(*)                      as item_count,
        count(distinct seller_id)     as seller_count,
        sum(price)                    as items_revenue,
        sum(freight_value)            as freight_total
    from {{ ref('stg_order_items') }}
    group by order_id

),

payments as (

    select
        order_id,
        count(*)            as payment_count,
        sum(payment_value)  as payment_total
    from {{ ref('stg_order_payments') }}
    group by order_id

),

reviews as (

    select order_id, review_score
    from {{ ref('stg_reviews') }}

),

joined as (

    select
        o.order_id,
        c.customer_unique_id                           as customer_key,
        cast(o.purchased_at as date)                   as order_date,
        o.order_status,
        o.order_status = 'delivered'                   as is_delivered,
        o.purchased_at,
        o.delivered_at,
        o.estimated_delivery_at,
        coalesce(i.item_count, 0)                      as item_count,
        coalesce(i.seller_count, 0)                    as seller_count,
        coalesce(i.items_revenue, 0)                   as items_revenue,
        coalesce(i.freight_total, 0)                   as freight_total,
        coalesce(p.payment_count, 0)                   as payment_count,
        coalesce(p.payment_total, 0)                   as payment_total,
        r.review_score
    from orders as o
    left join customers as c on o.customer_id = c.customer_id
    left join items     as i on o.order_id = i.order_id
    left join payments  as p on o.order_id = p.order_id
    left join reviews   as r on o.order_id = r.order_id

)

select
    order_id,
    customer_key,
    order_date,
    order_status,
    is_delivered,
    purchased_at,
    delivered_at,
    estimated_delivery_at,
    item_count,
    seller_count,
    items_revenue,
    -- Revenue counts delivered orders only (finding #3)
    case when is_delivered then items_revenue else 0 end   as delivered_revenue,
    freight_total,
    payment_count,
    payment_total,
    -- Delivery metrics need a delivered status AND a delivery date (findings #4, #5)
    case
        when is_delivered and delivered_at is not null
        then date_diff('day', purchased_at, delivered_at)
    end                                                     as delivery_days,
    case
        when is_delivered and delivered_at is not null
        then delivered_at > estimated_delivery_at
    end                                                     as is_late,
    review_score,
    order_date between cast('{{ var("analysis_start_date") }}' as date)
                   and cast('{{ var("analysis_end_date") }}' as date)   as in_analysis_window
from joined
