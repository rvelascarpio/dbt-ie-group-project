-- models/staging/stg_historical_weather_daily.sql
select
    city_name,
    date as weather_date,
    temperature_2m_max as temp_max_celsius,
    temperature_2m_min as temp_min_celsius,
    precipitation_sum as precipitation_mm
from {{ source('raw', 'historical_weather_daily') }}
