-- models/intermediate/int_air_quality_daily.sql
select
    location_id,
    city_name,
    country_code,
    cast(measured_at as date) as quality_date,
    avg(pm10_ug_m3) as avg_pm10_ug_m3,
    max(pm10_ug_m3) as max_pm10_ug_m3,
    avg(pm2_5_ug_m3) as avg_pm2_5_ug_m3,
    max(pm2_5_ug_m3) as max_pm2_5_ug_m3,
    avg(carbon_monoxide_ug_m3) as avg_carbon_monoxide_ug_m3,
    avg(nitrogen_dioxide_ug_m3) as avg_nitrogen_dioxide_ug_m3,
    avg(ozone_ug_m3) as avg_ozone_ug_m3,
    avg(european_aqi) as avg_european_aqi,
    max(european_aqi) as max_european_aqi,
    count(*) as hours_observed
from {{ ref('stg_air_quality_hourly') }}
group by 1, 2, 3, 4
