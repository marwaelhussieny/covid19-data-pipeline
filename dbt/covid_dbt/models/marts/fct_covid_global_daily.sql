-- Single global row per day, for the top-line dashboard KPI cards.

with country_daily as (

    select * from {{ ref('fct_covid_country_daily') }}

)

select
    report_date,
    sum(cumulative_confirmed) as global_cumulative_confirmed,
    sum(cumulative_deaths)    as global_cumulative_deaths,
    sum(new_confirmed)        as global_new_confirmed,
    sum(new_deaths)           as global_new_deaths,
    count(distinct country_region) as countries_reporting
from country_daily
group by 1
order by 1
