-- One row per product, with English category. Missing categories become 'unknown' (finding #10).
select
    p.product_id                                              as product_key,
    p.category_name_pt,
    coalesce(t.category_name_en, p.category_name_pt, 'unknown') as category_name_en,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm,
    p.photos_qty
from {{ ref('stg_products') }} as p
left join {{ ref('stg_category_translation') }} as t
    on p.category_name_pt = t.category_name_pt
