-- Every category must have exactly one row per week: rows = categories x weeks.
select r.row_count, c.categories, w.weeks
from (select count(*) as row_count from {{ ref('mart_weekly_category_demand') }}) as r
cross join (select count(distinct category) as categories from {{ ref('mart_weekly_category_demand') }}) as c
cross join (select count(distinct week_start) as weeks from {{ ref('mart_weekly_category_demand') }}) as w
where r.row_count <> c.categories * w.weeks
