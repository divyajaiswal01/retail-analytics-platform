-- Weekly units must equal delivered items in the same complete weeks (nothing lost or doubled).
with weeks as (

    select min(week_start) as first_week, max(week_start) as last_week
    from {{ ref('mart_weekly_category_demand') }}

)

select m.units as weekly_units, f.units as fact_units
from (select sum(units) as units from {{ ref('mart_weekly_category_demand') }}) as m
cross join (
    select count(*) as units
    from {{ ref('fact_order_items') }} as i
    cross join weeks as w
    where i.is_delivered
      and i.in_analysis_window
      and i.order_date between w.first_week and w.last_week + 6
) as f
where m.units <> f.units
