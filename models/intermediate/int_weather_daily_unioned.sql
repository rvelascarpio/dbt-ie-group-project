-- models/intermediate/int_weather_daily_unioned.sql
with recent as (

    select
        city_name,
        weather_date,
        temp_max_celsius,
        temp_min_celsius,
        precipitation_mm,
        wind_speed_max_kmh,
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
        wind_speed_max_kmh,
        'historical_weather' as data_source

    from {{ ref('stg_historical_weather_daily') }}

),

unioned as (

    select * from recent
    union all
    select * from historical

)

-- The recent (Forecast API, 92 days) and historical (Archive API) windows overlap.
-- Keep one row per city per day: prefer the historical/archive record where it
-- exists (the confirmed actuals); the recent source only fills the last few days
-- the archive has not published yet.
select
    city_name,
    weather_date,
    temp_max_celsius,
    temp_min_celsius,
    precipitation_mm,
    wind_speed_max_kmh,
    data_source
from unioned
qualify row_number() over (
    partition by city_name, weather_date
    order by case data_source when 'historical_weather' then 1 else 2 end
) = 1
