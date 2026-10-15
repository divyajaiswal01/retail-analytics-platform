-- One row per order item (grain). Used for category/seller analysis and the demand forecast.
select
    i.order_item_key,
    i.order_id,
    i.order_item_id,
    i.product_id                                     as product_key,
    i.seller_id                                      as seller_key,
    cast(o.purchased_at as date)                     as order_date,
    o.order_status,
    o.order_status = 'delivered'                     as is_delivered,
    i.price,
    i.freight_value,
    cast(o.purchased_at as date)
        between cast('{{ var("analysis_start_date") }}' as date)
            and cast('{{ var("analysis_end_date") }}' as date)  as in_analysis_window
from {{ ref('stg_order_items') }} as i
inner join {{ ref('stg_orders') }} as o
    on i.order_id = o.order_id
