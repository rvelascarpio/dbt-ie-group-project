-- models/intermediate/int_heatwave_events.sql
with hot_days as (

    select
        city_name,
        weather_date,
        temp_max_celsius
    from {{ ref('int_weather_daily_unioned') }}
    where temp_max_celsius > 35

),

grouped as (

    select
        city_name,
        weather_date,
        temp_max_celsius,
        weather_date - cast(row_number() over (partition by city_name order by weather_date) as integer) as island_id
    from hot_days

)

select
    city_name,
    min(weather_date) as start_date,
    max(weather_date) as end_date,
    count(*) as duration_days,
    max(temp_max_celsius) as peak_temp_max_celsius,
    avg(temp_max_celsius) as avg_temp_max_celsius
from grouped
group by city_name, island_id
order by city_name, start_date
