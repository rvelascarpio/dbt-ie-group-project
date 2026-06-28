-- models/intermediate/int_air_quality_alerts.sql
select
    location_id,
    city_name,
    country_code,
    quality_date,
    avg_pm2_5_ug_m3,
    avg_european_aqi,
    max_european_aqi,
    avg_pm2_5_ug_m3 > 15 as exceeds_who_pm2_5_guideline,
    avg_european_aqi >= 60 as exceeds_eu_aqi_poor_threshold
from {{ ref('int_air_quality_daily') }}
