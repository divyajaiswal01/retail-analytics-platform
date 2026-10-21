-- ISO day of week 1 = Monday. Any other day means the week boundaries are wrong.
select distinct week_start
from {{ ref('mart_weekly_category_demand') }}
where isodow(week_start) <> 1
