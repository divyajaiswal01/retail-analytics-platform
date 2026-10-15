-- One row per payment. An order can have several payments (finding #6),
-- so aggregate to order level before joining to orders.
select
    order_id || '-' || payment_sequential                 as payment_key,
    order_id,
    try_cast(payment_sequential as integer)               as payment_sequential,
    payment_type,
    try_cast(payment_installments as integer)             as payment_installments,
    try_cast(payment_value as decimal(12, 2))             as payment_value
from {{ source('raw', 'order_payments') }}
