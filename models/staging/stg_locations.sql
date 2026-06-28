-- models/staging/stg_locations.sql
select
    location_id,
    city_name,
    country,
    country_code,
    admin1 as region,
    latitude,
    longitude,
    timezone,
    elevation as elevation_meters,
    population,
    extracted_at
from {{ source('raw', 'locations') }}
