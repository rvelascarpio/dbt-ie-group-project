-- models/marts/dim_location.sql
select
    location_id,
    city_name,
    country,
    country_code,
    region,
    latitude,
    longitude,
    timezone,
    elevation_meters,
    population
from {{ ref('stg_locations') }}
