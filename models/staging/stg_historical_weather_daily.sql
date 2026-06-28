-- models/staging/stg_historical_weather_daily.sql
select
    -- historical_meteo.py hardcodes 'Sevilla'; every other extraction script resolves
    -- the city through the geocoding API, which returns 'Seville'. Conform here so
    -- this source joins correctly with the rest of the project on city_name.
    case city_name when 'Sevilla' then 'Seville' else city_name end as city_name,
    date as weather_date,
    temperature_2m_max as temp_max_celsius,
    temperature_2m_min as temp_min_celsius,
    precipitation_sum as precipitation_mm
from {{ source('raw', 'historical_weather_daily') }}
