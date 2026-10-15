-- fact_orders must have exactly one row per order: joins must not add or drop rows.
select f.row_count as fact_rows, s.row_count as staging_rows
from (select count(*) as row_count from {{ ref('fact_orders') }}) as f
cross join (select count(*) as row_count from {{ ref('stg_orders') }}) as s
where f.row_count <> s.row_count
