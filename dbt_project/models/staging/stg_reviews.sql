-- One review per order (finding #9). Raw data has orders with 2-3 reviews and
-- review_ids that repeat across orders, so keep the most recent review per order.
with source as (

    select
        order_id,
        review_id,
        try_cast(review_score as integer)                         as review_score,
        nullif(trim(review_comment_message), '')                  as comment_message,
        try_cast(review_creation_date as timestamp)               as created_at,
        try_cast(review_answer_timestamp as timestamp)            as answered_at
    from {{ source('raw', 'order_reviews') }}

),

ranked as (

    select
        order_id,
        review_id,
        review_score,
        comment_message,
        created_at,
        answered_at,
        row_number() over (
            partition by order_id
            order by answered_at desc nulls last, created_at desc nulls last, review_id desc
        ) as review_rank
    from source

)

select
    order_id,
    review_id,
    review_score,
    comment_message is not null  as has_comment,
    created_at,
    answered_at
from ranked
where review_rank = 1
