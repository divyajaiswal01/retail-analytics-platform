-- Portuguese -> English category names. Two categories used by products are missing
-- from the source file (finding #11), so they are added manually here.
with source as (

    select
        trim(product_category_name)          as category_name_pt,
        trim(product_category_name_english)  as category_name_en
    from {{ source('raw', 'category_translation') }}

),

manual as (

    select category_name_pt, category_name_en
    from (
        values
            ('pc_gamer', 'pc_gamer'),
            ('portateis_cozinha_e_preparadores_de_alimentos', 'portable_kitchen_and_food_preparers')
    ) as t(category_name_pt, category_name_en)

)

select category_name_pt, category_name_en from source
union all
select category_name_pt, category_name_en
from manual
where category_name_pt not in (select category_name_pt from source)
