-- Guards finding #5: delivery before purchase was 0 rows in the real data; keep it that way.
select order_id, delivery_days
from {{ ref('fact_orders') }}
where delivery_days < 0
