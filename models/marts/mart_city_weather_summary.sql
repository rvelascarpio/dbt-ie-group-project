-- models/marts/mart_city_weather_summary.sql
select
    weather.city_name,
    weather.weather_date,
    location.country,
    location.country_code,
    location.region,
    location.population,
    weather.temp_max_celsius,
    weather.temp_min_celsius,
    weather.precipitation_mm,
    air_quality.avg_pm2_5_ug_m3,
    air_quality.avg_european_aqi,
    air_quality.exceeds_who_pm2_5_guideline,
    air_quality.exceeds_eu_aqi_poor_threshold
from {{ ref('fct_city_weather_day') }} as weather
left join {{ ref('fct_air_quality_city_day') }} as air_quality
    on weather.city_name = air_quality.city_name
    and weather.weather_date = air_quality.quality_date
left join {{ ref('dim_location') }} as location
    on weather.city_name = location.city_name
