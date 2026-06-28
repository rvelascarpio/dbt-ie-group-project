-- models/intermediate/int_weather_daily_unioned.sql
with recent as (

    select
        city_name,
        weather_date,
        temp_max_celsius,
        temp_min_celsius,
        precipitation_mm,
        'recent_weather' as data_source

    from {{ ref('stg_weather_daily') }}

),

historical as (

    select
        city_name,
        weather_date,
        temp_max_celsius,
        temp_min_celsius,
        precipitation_mm,
        'historical_weather' as data_source

    from {{ ref('stg_historical_weather_daily') }}

)

select * from recent
union all
select * from historical
