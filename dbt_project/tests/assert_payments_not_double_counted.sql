-- Payments are one-to-many per order; the aggregated total must equal the raw total.
select f.total as fact_total, s.total as staging_total
from (select sum(payment_total) as total from {{ ref('fact_orders') }}) as f
cross join (select sum(payment_value) as total from {{ ref('stg_order_payments') }}) as s
where abs(f.total - s.total) > 0.01
