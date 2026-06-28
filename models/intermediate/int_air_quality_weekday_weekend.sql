-- models/intermediate/int_air_quality_weekday_weekend.sql
with daily as (

    select
        city_name,
        quality_date,
        case
            when extract(dow from quality_date) in (0, 6) then 'weekend'
            else 'weekday'
        end as day_type,
        avg_pm10_ug_m3,
        avg_pm2_5_ug_m3,
        avg_nitrogen_dioxide_ug_m3,
        avg_european_aqi
    from {{ ref('int_air_quality_daily') }}

)

select
    city_name,
    day_type,
    avg(avg_pm10_ug_m3) as avg_pm10_ug_m3,
    avg(avg_pm2_5_ug_m3) as avg_pm2_5_ug_m3,
    avg(avg_nitrogen_dioxide_ug_m3) as avg_nitrogen_dioxide_ug_m3,
    avg(avg_european_aqi) as avg_european_aqi,
    count(*) as days_observed
from daily
group by city_name, day_type
