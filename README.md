# Weather Analytics Engineering — Open-Meteo (Spain)

End-to-end analytics engineering project on Spanish weather and air quality, built
with **DuckDB + dbt Core + Streamlit**. Data is extracted from the free
[Open-Meteo](https://open-meteo.com) APIs, modeled through staging → intermediate →
marts, tested, and served in a **Weather Risk Monitor** dashboard.

Cities covered: **Madrid, Barcelona, Valencia, Seville, Bilbao**.

## 🔗 Dashboard

- **Live (Streamlit Community Cloud):** <https://dbt-ie-group-project-weather-risk-monitor.streamlit.app>
- **Run locally:** see [Launch the dashboard](#5-launch-the-dashboard) below.

The dashboard answers: **which cities experienced the most disruptive weather?**
It has city + date filters, 6+ charts/tables, metric definitions, and a note on the
grain of the main model. A "risk day" trips when the weather crosses the official
**AEMET** yellow-warning threshold for that city (heat / rain / gust) or the
**European AQI** "poor" band (air). Thresholds are per city because AEMET defines
"extreme" relative to each zone's climate.

---

## Project structure

```
.
├── data/
│   └── raw/open_meteo/          # raw CSVs (extraction output = dbt sources)
├── scripts/
│   ├── extract_open_meteo.py    # locations, recent weather, forecast, air quality
│   └── historical_meteo.py      # historical daily weather 2023 -> today (Archive API)
├── models/
│   ├── staging/                 # stg_* : one view per raw source
│   ├── intermediate/            # int_* : joins, aggregations, unions
│   └── marts/                   # dim_/fct_/mart_ : final tables
├── streamlit_app/
│   └── app.py                   # Weather Risk Monitor dashboard
├── .streamlit/config.toml       # dashboard theme
├── create_db.py                 # loads the raw CSVs into DuckDB
├── dbt_project.yml
├── profiles.yml
├── packages.yml
├── pyproject.toml
└── README.md
```

---

## How to run it

Everything is run from the project root. Requires [uv](https://docs.astral.sh/uv/)
(or any Python 3.10–3.12 environment).

### 1. Install dependencies

```bash
uv sync          # Python deps (dbt, duckdb, streamlit, plotly, pandas)
uv run dbt deps  # dbt packages (dbt_utils, dbt_expectations, codegen, dbt_date)
```

### 2. Get the raw data

The raw CSVs are already committed under `data/raw/open_meteo/`, so you can skip
straight to step 3. To **reproduce** them from the API:

```bash
# recent weather (92 days), 7-day forecast, and air quality (2023 -> today)
uv run python scripts/extract_open_meteo.py --past-days 92

# historical daily weather 2023 -> ~5 days ago (Archive API, with wind)
uv run python scripts/historical_meteo.py
```

These write to `data/raw/open_meteo/`. No API key is required.

### 3. Load the data into DuckDB

```bash
uv run python create_db.py
```

This reads every CSV in `data/raw/open_meteo/` and creates one table per file in
`my_database.duckdb` (stripping the `raw_` prefix). Those tables are the dbt sources.

### 4. Run dbt

```bash
uv run dbt build   # runs + tests every model (staging → intermediate → marts)
```

You should see all models and tests pass.

### 5. Launch the dashboard

```bash
uv run streamlit run streamlit_app/app.py
```

Opens at `http://localhost:8501`.

---

## Data model

Sources → Staging → Intermediate → Marts.

- **Sources** (`models/sources.yml`): 6 raw tables loaded by `create_db.py`.
- **Staging** (`stg_*`, views): one per source; rename to snake_case, cast types,
  keep the source grain.
- **Intermediate** (`int_*`): unions and aggregations, e.g. `int_weather_daily_unioned`
  stitches the recent + historical weather into one continuous series (2023 → today),
  and `int_air_quality_daily` rolls hourly air quality up to a daily grain.
- **Marts** (`dim_*`, `fct_*`, `mart_*`): the final tables the dashboard reads.

### Final models powering the dashboard

| Model | Grain | Used for |
|---|---|---|
| `fct_city_weather_day` | one row per city per day | heat / rain / wind risk (2023 → today) |
| `fct_air_quality_city_day` | one row per city per day | air-quality risk (days + poor-air hours) |
| `dim_location` | one row per city | country, region, population |
| `mart_heatwave_events` | one row per heat-streak event | heatwave table |
| `fct_weather_forecast_day` | one row per city per forecast day | 7-day risk forecast panel |

---

## Modeling choices

- **Continuous weather series.** Weather comes from two APIs: the Archive API for
  history (2023 → ~5 days ago, deep but lagging) and the Forecast API `past_days`
  for the last few days up to today. `int_weather_daily_unioned` unions them and
  keeps one row per city per day (preferring the archive record on overlapping
  dates), so there is no gap.
- **Wind uses gusts.** AEMET's wind warnings are gust-based, so we carry
  `wind_gust_max_kmh` through the models and compare against it.
- **Air quality aggregated to daily.** Hourly observations are rolled up in
  `int_air_quality_daily`, which also counts `poor_air_hours` (hours with European
  AQI ≥ 60) so the dashboard can report poor air in hours as well as days.
- **Thresholds live in the dashboard**, not in dbt, so they can be per-city
  (official AEMET values) and toggled to custom values interactively.

### Data tests

Every mart is tested (`uv run dbt test`) for: unique keys
(`dbt_utils.unique_combination_of_columns`), not-null keys and dates, relationships
to `dim_location`, accepted values for categorical fields, and reasonable metric
ranges (`dbt_expectations.expect_column_values_to_be_between`).

---

## Risk thresholds

| Risk | Threshold | Source |
|---|---|---|
| 🔥 Extreme heat | daily max temp over the city's AEMET yellow limit (34–38 °C) | AEMET Plan Meteoalerta |
| 🌧️ Heavy rain | precipitation over the city's AEMET 12 h limit (40–60 mm) | AEMET Plan Meteoalerta |
| 💨 High wind | wind gust over the city's AEMET limit (70–90 km/h) | AEMET Plan Meteoalerta |
| 🏭 Poor air | average European AQI ≥ 60 ("poor" band) | European Environment Agency |

Thresholds are per city (see the sidebar in the dashboard). The forecast panel uses
the same heat/rain/wind thresholds; it has no air quality.
