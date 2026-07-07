with source as (

    select * from {{ source('raw', 'covid_daily') }}

),

renamed as (

    select
        cast(date as date)                     as report_date,
        country_region,
        province_state,
        latitude,
        longitude,
        coalesce(cumulative_confirmed, 0)       as cumulative_confirmed,
        coalesce(cumulative_deaths, 0)          as cumulative_deaths,
        coalesce(new_confirmed, 0)              as new_confirmed,
        coalesce(new_deaths, 0)                 as new_deaths,
        is_data_correction

    from source

)

select * from renamed
