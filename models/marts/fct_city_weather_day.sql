-- models/marts/fct_city_weather_day.sql
select
    city_name,
    weather_date,
    data_source,
    temp_max_celsius,
    temp_min_celsius,
    precipitation_mm,
    wind_speed_max_kmh,
    wind_gust_max_kmh
from {{ ref('int_weather_daily_unioned') }}
