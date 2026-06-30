-- models/marts/fct_forecast_city_day.sql
select
    city_name,
    forecast_date,
    forecast_temp_max_celsius,
    actual_temp_max_celsius,
    temp_max_error_celsius,
    forecast_temp_min_celsius,
    actual_temp_min_celsius,
    temp_min_error_celsius,
    forecast_precipitation_mm,
    actual_precipitation_mm,
    precipitation_error_mm,
    forecast_wind_speed_max_kmh,
    actual_wind_speed_max_kmh,
    wind_speed_max_error_kmh
from {{ ref('int_weather_forecast_accuracy') }}
