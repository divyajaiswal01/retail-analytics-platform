-- One row per real customer (customer_unique_id), finding #1.
-- A customer who ordered several times has several customer_ids; keep the most recent record.
with customer_orders as (

    select
        c.customer_unique_id,
        c.zip_prefix,
        c.city,
        c.state,
        row_number() over (
            partition by c.customer_unique_id
            order by o.purchased_at desc nulls last, c.customer_id desc
        ) as record_rank
    from {{ ref('stg_customers') }} as c
    left join {{ ref('stg_orders') }} as o
        on c.customer_id = o.customer_id

)

select
    customer_unique_id  as customer_key,
    zip_prefix,
    city,
    state
from customer_orders
where record_rank = 1
