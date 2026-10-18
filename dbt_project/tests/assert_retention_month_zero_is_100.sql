-- Every cohort is 100% active in its own first month, and retention can never exceed 100%.
select cohort_month, months_since_first, retention_pct
from {{ ref('mart_cohort_retention') }}
where (months_since_first = 0 and retention_pct <> 100)
   or retention_pct > 100
   or retention_pct < 0
