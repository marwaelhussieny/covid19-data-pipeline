-- One row per country/day: rolls up province/state level data (matches
-- the project brief's ask for "resource planning" at a regional level).

with staged as (

    select * from {{ ref('stg_covid_daily') }}

),

country_daily as (

    select
        report_date,
        country_region,
        sum(cumulative_confirmed) as cumulative_confirmed,
        sum(cumulative_deaths)    as cumulative_deaths,
        sum(new_confirmed)        as new_confirmed,
        sum(new_deaths)           as new_deaths,
        bool_or(is_data_correction) as had_data_correction

    from staged
    group by 1, 2

)

select
    *,
    case when cumulative_confirmed > 0
         then round(100.0 * cumulative_deaths / cumulative_confirmed, 3)
         else null
    end as case_fatality_rate_pct,
    -- 7-day rolling average smooths day-of-week reporting noise
    avg(new_confirmed) over (
        partition by country_region
        order by report_date
        rows between 6 preceding and current row
    ) as new_confirmed_7day_avg
from country_daily
