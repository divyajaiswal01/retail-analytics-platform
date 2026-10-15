-- One row per customer_id (a per-order identifier). The real person is customer_unique_id.
select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix     as zip_prefix,
    lower(trim(customer_city))   as city,
    upper(trim(customer_state))  as state
from {{ source('raw', 'customers') }}
