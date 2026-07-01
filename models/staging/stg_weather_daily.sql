-- models/staging/stg_weather_daily.sql
select
    source_name,
    extracted_at,
    location_id,
    city_name,
    country_code,
    date as weather_date,
    latitude,
    longitude,
    timezone,
    temperature_2m_max as temp_max_celsius,
    temperature_2m_min as temp_min_celsius,
    temperature_2m_mean as temp_mean_celsius,
    precipitation_sum as precipitation_mm,
    rain_sum as rain_mm,
    snowfall_sum as snowfall_cm,
    wind_speed_10m_max as wind_speed_max_kmh,
    wind_gusts_10m_max as wind_gust_max_kmh
from {{ source('raw', 'weather_daily') }}
