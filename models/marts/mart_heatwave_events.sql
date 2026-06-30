-- models/marts/mart_heatwave_events.sql
select
    heatwave.city_name,
    heatwave.start_date,
    heatwave.end_date,
    heatwave.duration_days,
    heatwave.peak_temp_max_celsius,
    heatwave.avg_temp_max_celsius,
    location.country,
    location.country_code,
    location.region,
    location.population
from {{ ref('int_heatwave_events') }} as heatwave
left join {{ ref('dim_location') }} as location
    on heatwave.city_name = location.city_name
