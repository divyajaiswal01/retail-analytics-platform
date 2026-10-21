-- No forecast input week may extend past the verified-complete data or the analysis window.
select max(week_start) as last_week_start
from {{ ref('mart_weekly_category_demand') }}
having max(week_start) + 6 > cast('{{ var("data_complete_through") }}' as date)
    or max(week_start) + 6 > cast('{{ var("analysis_end_date") }}' as date)
