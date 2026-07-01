-- models/marts/fct_weather_forecast_day.sql
-- Forward-looking daily weather forecast (next 7 days) used by the Streamlit
-- "risk forecast" panel. One row per city per forecast date; if the forecast has
-- been extracted more than once, the most recent run wins.
select
    city_name,
    forecast_date,
    extracted_at,
    temp_max_celsius,
    temp_min_celsius,
    precipitation_mm,
    wind_gust_max_kmh
from {{ ref('stg_forecast_daily') }}
qualify row_number() over (
    partition by city_name, forecast_date
    order by extracted_at desc
) = 1
