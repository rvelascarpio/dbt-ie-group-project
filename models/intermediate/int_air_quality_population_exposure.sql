-- models/intermediate/int_air_quality_population_exposure.sql
with air_quality as (

    select * from {{ ref('int_air_quality_daily') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    air_quality.city_name,
    air_quality.quality_date,
    locations.population,
    locations.elevation_meters,
    air_quality.avg_pm2_5_ug_m3,
    air_quality.avg_european_aqi,
    air_quality.avg_pm2_5_ug_m3 * locations.population as pm2_5_population_exposure_index
from air_quality
inner join locations
    on air_quality.location_id = locations.location_id
