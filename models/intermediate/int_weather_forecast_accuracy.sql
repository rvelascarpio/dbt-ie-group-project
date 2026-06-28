-- models/intermediate/int_weather_forecast_accuracy.sql
with forecast as (

    select * from {{ ref('stg_weather_forecast_7d') }}

),

actual as (

    select * from {{ ref('stg_weather_daily') }}

)

select
    forecast.city_name,
    forecast.forecast_date,
    forecast.temp_max_celsius as forecast_temp_max_celsius,
    actual.temp_max_celsius as actual_temp_max_celsius,
    forecast.temp_max_celsius - actual.temp_max_celsius as temp_max_error_celsius,
    forecast.temp_min_celsius as forecast_temp_min_celsius,
    actual.temp_min_celsius as actual_temp_min_celsius,
    forecast.temp_min_celsius - actual.temp_min_celsius as temp_min_error_celsius,
    forecast.precipitation_mm as forecast_precipitation_mm,
    actual.precipitation_mm as actual_precipitation_mm,
    forecast.precipitation_mm - actual.precipitation_mm as precipitation_error_mm,
    forecast.wind_speed_max_kmh as forecast_wind_speed_max_kmh,
    actual.wind_speed_max_kmh as actual_wind_speed_max_kmh,
    forecast.wind_speed_max_kmh - actual.wind_speed_max_kmh as wind_speed_max_error_kmh
from forecast
inner join actual
    on forecast.city_name = actual.city_name
    and forecast.forecast_date = actual.weather_date
