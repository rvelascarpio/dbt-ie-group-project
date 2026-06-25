-- models/staging/stg_air_quality_hourly.sql
select
    source_name,
    extracted_at,
    location_id,
    city_name,
    country_code,
    timestamp as measured_at,
    latitude,
    longitude,
    timezone,
    pm10 as pm10_ug_m3,
    pm2_5 as pm2_5_ug_m3,
    carbon_monoxide as carbon_monoxide_ug_m3,
    nitrogen_dioxide as nitrogen_dioxide_ug_m3,
    ozone as ozone_ug_m3,
    european_aqi
from {{ source('raw', 'air_quality_hourly') }}
