-- Every staged item must appear exactly once in fact_order_items.
select f.row_count as fact_rows, s.row_count as staging_rows
from (select count(*) as row_count from {{ ref('fact_order_items') }}) as f
cross join (select count(*) as row_count from {{ ref('stg_order_items') }}) as s
where f.row_count <> s.row_count
