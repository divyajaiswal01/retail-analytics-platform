-- One row per product. Fixes the source's misspelled "lenght" columns.
-- Zero weights are treated as missing (finding #12).
select
    product_id,
    nullif(trim(product_category_name), '')                   as category_name_pt,
    try_cast(product_name_lenght as integer)                  as name_length,
    try_cast(product_description_lenght as integer)           as description_length,
    try_cast(product_photos_qty as integer)                   as photos_qty,
    nullif(try_cast(product_weight_g as double), 0)           as weight_g,
    try_cast(product_length_cm as double)                     as length_cm,
    try_cast(product_height_cm as double)                     as height_cm,
    try_cast(product_width_cm as double)                      as width_cm
from {{ source('raw', 'products') }}
