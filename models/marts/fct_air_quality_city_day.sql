-- models/marts/fct_air_quality_city_day.sql
with air_quality as (

    select * from {{ ref('int_air_quality_daily') }}

),

alerts as (

    select
        city_name,
        quality_date,
        exceeds_who_pm2_5_guideline,
        exceeds_eu_aqi_poor_threshold
    from {{ ref('int_air_quality_alerts') }}

),

exposure as (

    select
        city_name,
        quality_date,
        population,
        pm2_5_population_exposure_index
    from {{ ref('int_air_quality_population_exposure') }}

)

select
    air_quality.location_id,
    air_quality.city_name,
    air_quality.country_code,
    air_quality.quality_date,
    air_quality.avg_pm10_ug_m3,
    air_quality.max_pm10_ug_m3,
    air_quality.avg_pm2_5_ug_m3,
    air_quality.max_pm2_5_ug_m3,
    air_quality.avg_carbon_monoxide_ug_m3,
    air_quality.avg_nitrogen_dioxide_ug_m3,
    air_quality.avg_ozone_ug_m3,
    air_quality.avg_european_aqi,
    air_quality.max_european_aqi,
    air_quality.hours_observed,
    alerts.exceeds_who_pm2_5_guideline,
    alerts.exceeds_eu_aqi_poor_threshold,
    exposure.population,
    exposure.pm2_5_population_exposure_index
from air_quality
left join alerts
    on air_quality.city_name = alerts.city_name
    and air_quality.quality_date = alerts.quality_date
left join exposure
    on air_quality.city_name = exposure.city_name
    and air_quality.quality_date = exposure.quality_date
