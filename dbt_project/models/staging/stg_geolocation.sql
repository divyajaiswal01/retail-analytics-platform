{{ config(materialized='table') }}
-- Raw geolocation has ~50 rows per zip prefix (finding #15), so joining it directly
-- would multiply rows. Reduce to one row per zip using the median (robust to bad points).
select
    geolocation_zip_code_prefix                              as zip_prefix,
    median(try_cast(geolocation_lat as double))              as latitude,
    median(try_cast(geolocation_lng as double))              as longitude,
    mode(upper(trim(geolocation_state)))                     as state,
    count(*)                                                 as source_row_count
from {{ source('raw', 'geolocation') }}
group by geolocation_zip_code_prefix
