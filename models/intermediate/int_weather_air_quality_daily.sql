-- models/intermediate/int_weather_air_quality_daily.sql
with weather as (

    select * from {{ ref('stg_weather_daily') }}

),

air_quality as (

    select * from {{ ref('int_air_quality_daily') }}

)

select
    weather.city_name,
    weather.weather_date,
    weather.temp_max_celsius,
    weather.temp_min_celsius,
    weather.temp_mean_celsius,
    weather.precipitation_mm,
    weather.rain_mm,
    weather.snowfall_cm,
    weather.wind_speed_max_kmh,
    air_quality.avg_pm10_ug_m3,
    air_quality.max_pm10_ug_m3,
    air_quality.avg_pm2_5_ug_m3,
    air_quality.max_pm2_5_ug_m3,
    air_quality.avg_carbon_monoxide_ug_m3,
    air_quality.avg_nitrogen_dioxide_ug_m3,
    air_quality.avg_ozone_ug_m3,
    air_quality.avg_european_aqi,
    air_quality.max_european_aqi
from weather
inner join air_quality
    on weather.city_name = air_quality.city_name
    and weather.weather_date = air_quality.quality_date
