-- models/intermediate/int_weather_monthly_summary.sql
select
    city_name,
    date_trunc('month', weather_date)::date as month_start,
    extract(year from weather_date) as year,
    extract(month from weather_date) as month,
    avg(temp_max_celsius) as avg_temp_max_celsius,
    avg(temp_min_celsius) as avg_temp_min_celsius,
    sum(precipitation_mm) as total_precipitation_mm,
    count(*) as days_observed,
    max(data_source) as data_source
from {{ ref('int_weather_daily_unioned') }}
group by 1, 2, 3, 4
