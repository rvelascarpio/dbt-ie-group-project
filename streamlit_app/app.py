"""Weather Risk Monitor — Streamlit dashboard for the Open-Meteo group project.

Reads from the final dbt mart/fact models in the DuckDB database (never the raw
API files). Answers: which cities experienced the most disruptive weather?

Risk thresholds
---------------
By default a day is "risky" when it would trip AEMET's official *yellow* warning
(aviso amarillo) for that city's zone — see CITY_THRESHOLDS. Air quality uses the
European AQI "poor" band (>= 60), which also matches the project's dbt models.

Two honest caveats about matching AEMET exactly:
  - Rain: AEMET thresholds are per 12 h; our data is a daily (24 h) total, so the
    12 h yellow value is used as a daily proxy.
  - Wind: AEMET measures gusts (racha máxima), so we compare against
    `wind_gust_max_kmh`, not the sustained `wind_speed_max_kmh`.

Main model grain
----------------
`fct_city_weather_day`: one row per city per day (2023-01-01 -> today), enriched
with `fct_air_quality_city_day` (same grain) and `dim_location` (one per city).
`mart_heatwave_events` is one row per heat-streak event per city.

Run it
------
    uv run streamlit run streamlit_app/app.py

Requires the DuckDB database. Build it first:
    uv run python create_db.py && uv run dbt build
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "my_database.duckdb"

# Official AEMET yellow-warning (aviso amarillo) thresholds for each city's zone.
# Source: AEMET Plan Meteoalerta, Anexo 1 (Umbrales y niveles de aviso, 2022).
#   heat      = max temperature (°C)              [same window as our data]
#   rain_12h  = precipitation in 12 h (mm)        [used as a daily proxy]
#   wind_gust = max wind gust / racha máxima (km/h)
CITY_THRESHOLDS = {
    "Madrid": {"zone": "Metropolitana y Henares", "heat": 36, "rain_12h": 40, "wind_gust": 70},
    "Barcelona": {"zone": "Litoral de Barcelona", "heat": 34, "rain_12h": 60, "wind_gust": 70},
    "Valencia": {"zone": "Litoral norte de Valencia", "heat": 36, "rain_12h": 60, "wind_gust": 70},
    "Seville": {"zone": "Campiña sevillana", "heat": 38, "rain_12h": 40, "wind_gust": 70},
    "Bilbao": {"zone": "Bizkaia litoral", "heat": 34, "rain_12h": 40, "wind_gust": 90},
}
AQI_POOR = 60  # European AQI "poor" band (official EEA scale)

st.set_page_config(page_title="Weather Risk Monitor", page_icon="⛈️", layout="wide")

# White background + larger, readable text for all Plotly charts.
pio.templates["plotly_white"].layout.font.size = 15
px.defaults.template = "plotly_white"


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading data from DuckDB…")
def load_data() -> dict[str, pd.DataFrame]:
    """Load the mart/fact tables the dashboard needs."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        weather = con.execute(
            """
            select
                w.city_name,
                w.weather_date,
                w.temp_max_celsius,
                w.temp_min_celsius,
                w.precipitation_mm,
                w.wind_speed_max_kmh,
                w.wind_gust_max_kmh,
                l.country,
                l.region,
                l.population
            from fct_city_weather_day as w
            left join dim_location as l on w.city_name = l.city_name
            """
        ).df()

        air = con.execute(
            """
            select
                city_name,
                quality_date as weather_date,
                avg_european_aqi,
                max_european_aqi,
                avg_pm2_5_ug_m3,
                poor_air_hours
            from fct_air_quality_city_day
            """
        ).df()

        heatwaves = con.execute("select * from mart_heatwave_events").df()

        forecast = con.execute(
            """
            select
                city_name,
                forecast_date,
                temp_max_celsius,
                precipitation_mm,
                wind_gust_max_kmh
            from fct_weather_forecast_day
            """
        ).df()
    finally:
        con.close()

    weather["weather_date"] = pd.to_datetime(weather["weather_date"])
    air["weather_date"] = pd.to_datetime(air["weather_date"])
    heatwaves["start_date"] = pd.to_datetime(heatwaves["start_date"])
    heatwaves["end_date"] = pd.to_datetime(heatwaves["end_date"])
    forecast["forecast_date"] = pd.to_datetime(forecast["forecast_date"])

    daily = weather.merge(air, on=["city_name", "weather_date"], how="left")
    return {"daily": daily, "heatwaves": heatwaves, "forecast": forecast}


def compute_forecast_risk(fc: pd.DataFrame) -> pd.DataFrame:
    """Risk flags for the forecast, using official AEMET per-city thresholds.

    Only 3 alarms (heat, rain, wind) — the forecast has no air quality.
    """
    fc = fc.copy()
    heat_thr = fc["city_name"].map(lambda c: CITY_THRESHOLDS.get(c, {}).get("heat"))
    rain_thr = fc["city_name"].map(lambda c: CITY_THRESHOLDS.get(c, {}).get("rain_12h"))
    wind_thr = fc["city_name"].map(lambda c: CITY_THRESHOLDS.get(c, {}).get("wind_gust"))
    fc["is_heat"] = (fc["temp_max_celsius"] > heat_thr).fillna(False)
    fc["is_rain"] = (fc["precipitation_mm"] > rain_thr).fillna(False)
    fc["is_wind"] = (fc["wind_gust_max_kmh"] > wind_thr).fillna(False)
    fc["risk_score"] = (
        fc["is_heat"].astype(int)
        + fc["is_rain"].astype(int)
        + fc["is_wind"].astype(int)
    )
    return fc


def _threshold(df: pd.DataFrame, key: str, override: float | None) -> pd.Series:
    """Per-city official threshold, or a single override value for all cities."""
    if override is not None:
        return pd.Series(override, index=df.index)
    return df["city_name"].map(lambda c: CITY_THRESHOLDS.get(c, {}).get(key))


def compute_risk(df: pd.DataFrame, aqi: int, override: dict | None) -> pd.DataFrame:
    """Add boolean risk flags and a 0-4 risk score using per-city thresholds."""
    df = df.copy()
    heat_thr = _threshold(df, "heat", override.get("heat") if override else None)
    rain_thr = _threshold(df, "rain_12h", override.get("rain_12h") if override else None)
    wind_thr = _threshold(df, "wind_gust", override.get("wind_gust") if override else None)

    df["is_heat"] = (df["temp_max_celsius"] > heat_thr).fillna(False)
    df["is_rain"] = (df["precipitation_mm"] > rain_thr).fillna(False)
    # Wind uses gusts (to match AEMET's racha); air quality may have gaps.
    df["is_wind"] = (df["wind_gust_max_kmh"] > wind_thr).fillna(False)
    df["is_poor_air"] = (df["avg_european_aqi"] >= aqi).fillna(False)
    df["risk_score"] = (
        df["is_heat"].astype(int)
        + df["is_rain"].astype(int)
        + df["is_wind"].astype(int)
        + df["is_poor_air"].astype(int)
    )
    df["is_risky"] = df["risk_score"] > 0
    return df


def longest_streak(df: pd.DataFrame) -> tuple[int, str]:
    """Longest run of consecutive risky days across the selected cities."""
    best_len, best_city = 0, "—"
    for city, g in df.sort_values("weather_date").groupby("city_name"):
        run = 0
        for flag in g["is_risky"].to_numpy():
            run = run + 1 if flag else 0
            if run > best_len:
                best_len, best_city = run, city
    return best_len, best_city


# ---------------------------------------------------------------------------
# Guard: database must exist
# ---------------------------------------------------------------------------
if not DB_PATH.exists():
    st.error(
        f"Database not found at `{DB_PATH}`.\n\n"
        "Build it first from the project root:\n\n"
        "```\nuv run python create_db.py && uv run dbt build\n```"
    )
    st.stop()

data = load_data()
daily_all = data["daily"]
heatwaves_all = data["heatwaves"]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("⛈️ Weather Risk Monitor")
st.markdown(
    "#### Which cities experienced the most disruptive weather?"
)
st.markdown(
    "Data: Open-Meteo → dbt marts → DuckDB &nbsp;·&nbsp; "
    "Main grain: **one row per city per day** (`fct_city_weather_day`) &nbsp;·&nbsp; "
    "Risk = official **AEMET yellow-warning** thresholds per city."
)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

all_cities = sorted(daily_all["city_name"].dropna().unique())
cities = st.sidebar.multiselect("Cities", all_cities, default=all_cities)

min_d = daily_all["weather_date"].min().date()
max_d = daily_all["weather_date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d
)

st.sidebar.header("Risk thresholds")
use_official = st.sidebar.checkbox(
    "Use official thresholds (AEMET + European AQI)", value=True
)
override = None
if use_official:
    aqi = AQI_POOR
    st.sidebar.caption("Official limits — 🔥 heat / 🌧️ rain 12h / 💨 gust (AEMET, per city):")
    st.sidebar.markdown(
        "\n".join(
            f"- **{c}**: {t['heat']}°C / {t['rain_12h']}mm / {t['wind_gust']}km/h"
            for c, t in CITY_THRESHOLDS.items()
        )
    )
    st.sidebar.caption(f"🏭 Poor air: European AQI ≥ {AQI_POOR} (EEA “poor” band, all cities)")
else:
    st.sidebar.caption("Custom thresholds applied to every city:")
    override = {
        "heat": st.sidebar.slider("Extreme heat — max temp > (°C)", 25.0, 45.0, 35.0, 0.5),
        "rain_12h": st.sidebar.slider("Heavy rain — precip > (mm)", 5.0, 80.0, 40.0, 1.0),
        "wind_gust": st.sidebar.slider("High wind — gust > (km/h)", 30.0, 120.0, 70.0, 1.0),
    }
    aqi = st.sidebar.slider("Poor air — avg European AQI ≥", 20, 100, AQI_POOR, 5)

with st.sidebar.expander("ℹ️ Metric definitions"):
    st.markdown(
        f"""
        A **risky day** trips at least one flag. **Risk score** = flags tripped (0–4).

        - 🔥 **Extreme heat** — `temp_max_celsius` over the threshold
        - 🌧️ **Heavy rain** — `precipitation_mm` over the threshold
        - 💨 **High wind** — `wind_gust_max_kmh` (gust) over the threshold
        - 🏭 **Poor air** — `avg_european_aqi` ≥ {aqi}

        Default thresholds are **AEMET yellow-warning** values for each city's zone
        (rain uses the 12 h value as a daily proxy; wind uses gusts).
        Missing wind/air values count as “not risky”.
        """
    )

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
if len(date_range) != 2:
    st.warning("Pick a start and end date.")
    st.stop()
start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

mask = (
    daily_all["city_name"].isin(cities)
    & (daily_all["weather_date"] >= start)
    & (daily_all["weather_date"] <= end)
)
daily = compute_risk(daily_all[mask], aqi, override)

if daily.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
streak_len, streak_city = longest_streak(daily)
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Risky city-days", f"{int(daily['is_risky'].sum()):,}")
c2.metric("🔥 Heat days", f"{int(daily['is_heat'].sum()):,}")
c3.metric("🌧️ Rain days", f"{int(daily['is_rain'].sum()):,}")
c4.metric("💨 Wind days", f"{int(daily['is_wind'].sum()):,}")
c5.metric("🏭 Poor-air days", f"{int(daily['is_poor_air'].sum()):,}")
c6.metric("🏭 Poor-air hours", f"{int(daily['poor_air_hours'].fillna(0).sum()):,}",
          help="Hours with European AQI ≥ 60 (poor band)")
c7.metric("📅 Longest risky streak", f"{streak_len} d", help=f"City: {streak_city}")

st.divider()

# ---------------------------------------------------------------------------
# Chart 1 — Risk breakdown by city
# ---------------------------------------------------------------------------
st.subheader("Risk days by city")
by_city = (
    daily.groupby("city_name")[["is_heat", "is_rain", "is_wind", "is_poor_air"]]
    .sum()
    .rename(
        columns={
            "is_heat": "🔥 Heat",
            "is_rain": "🌧️ Rain",
            "is_wind": "💨 Wind",
            "is_poor_air": "🏭 Poor air",
        }
    )
    .reset_index()
    .melt(id_vars="city_name", var_name="Risk type", value_name="Days")
)
fig1 = px.bar(
    by_city.sort_values("Days"),
    x="Days",
    y="city_name",
    color="Risk type",
    orientation="h",
    title="Number of risky days per city, by risk type",
)
fig1.update_layout(yaxis_title="", legend_title="")
st.plotly_chart(fig1, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 2 — Daily risk timeline
# ---------------------------------------------------------------------------
st.subheader("Daily risk timeline")
st.caption(
    "One line per city. Click a city in the legend to hide/show it; "
    "double-click to isolate just one."
)
timeline = (
    daily.groupby(["weather_date", "city_name"])["risk_score"]
    .sum()
    .reset_index(name="Risk score")
)
fig2 = px.line(
    timeline, x="weather_date", y="Risk score", color="city_name",
    title="Daily risk score by city",
)
fig2.update_layout(xaxis_title="", yaxis_title="Risk score (0-4)", legend_title="City")
# Show every month on the x-axis (dense over multiple years; clearer when filtered).
fig2.update_xaxes(dtick="M1", tickformat="%b %Y", tickangle=-45)
st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 3 — Risk calendar heatmap (city × month)
# ---------------------------------------------------------------------------
st.subheader("Risk calendar (risky days per month)")
cal = daily.copy()
cal["month"] = cal["weather_date"].dt.to_period("M").dt.to_timestamp()
heat = cal.groupby(["city_name", "month"])["is_risky"].sum().reset_index(name="risky_days")
pivot = heat.pivot(index="city_name", columns="month", values="risky_days").fillna(0)
pivot.columns = [c.strftime("%Y-%m") for c in pivot.columns]
fig3 = px.imshow(
    pivot, aspect="auto", color_continuous_scale="OrRd",
    labels=dict(x="Month", y="", color="Risky days"),
    title="Risky days per city per month",
)
# Force every month label to show on the x-axis (plotly hides some by default).
fig3.update_xaxes(tickmode="linear", dtick=1, tickangle=-45)
st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 4 — Top 10 most extreme city-days
# ---------------------------------------------------------------------------
st.subheader("Top 10 most extreme city-days")
top = (
    daily.sort_values(
        ["risk_score", "temp_max_celsius", "precipitation_mm", "wind_gust_max_kmh"],
        ascending=False,
    )
    .head(10)
    .assign(date=lambda d: d["weather_date"].dt.date)
)
st.dataframe(
    top[
        ["date", "city_name", "risk_score", "temp_max_celsius",
         "precipitation_mm", "wind_gust_max_kmh", "avg_european_aqi"]
    ].rename(
        columns={
            "city_name": "city",
            "risk_score": "risk (0-4)",
            "temp_max_celsius": "temp max °C",
            "precipitation_mm": "precip mm",
            "wind_gust_max_kmh": "gust km/h",
            "avg_european_aqi": "avg AQI",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Air quality panel
# ---------------------------------------------------------------------------
st.subheader("🏭 Air quality (European AQI)")
air = daily.dropna(subset=["avg_european_aqi"])
if air.empty:
    st.info("No air quality data for the selected filters.")
else:
    fig4 = px.line(
        air.sort_values("weather_date"),
        x="weather_date", y="avg_european_aqi", color="city_name",
        title="Daily average European AQI by city",
    )
    fig4.add_hline(
        y=aqi, line_dash="dash", line_color="red",
        annotation_text=f"Poor-air threshold ({aqi})",
    )
    fig4.update_layout(xaxis_title="", yaxis_title="Avg European AQI", legend_title="")
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# Heatwave events table
# ---------------------------------------------------------------------------
st.subheader("🔥 Heatwave events (streaks of days > 35 °C)")
hw = heatwaves_all[
    heatwaves_all["city_name"].isin(cities)
    & (heatwaves_all["end_date"] >= start)
    & (heatwaves_all["start_date"] <= end)
].copy()
if hw.empty:
    st.info("No heatwave events for the selected filters.")
else:
    hw["start"] = hw["start_date"].dt.date
    hw["end"] = hw["end_date"].dt.date
    st.dataframe(
        hw.sort_values("duration_days", ascending=False)[
            ["city_name", "start", "end", "duration_days", "peak_temp_max_celsius"]
        ].rename(
            columns={
                "city_name": "city",
                "duration_days": "days",
                "peak_temp_max_celsius": "peak °C",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Risk forecast — next 7 days
# ---------------------------------------------------------------------------
st.subheader("⛈️ Risk forecast — next 7 days")
st.caption(
    "Upcoming risk from the Open-Meteo forecast, using the same official AEMET "
    "thresholds per city. Only 3 alarms here (🔥 heat / 🌧️ rain / 💨 gust) — the "
    "forecast has no air quality. Not affected by the date filter above."
)
fc = compute_forecast_risk(
    data["forecast"][data["forecast"]["city_name"].isin(cities)]
)
if fc.empty:
    st.info("No forecast data for the selected cities.")
else:
    fc = fc.sort_values(["city_name", "forecast_date"])
    fc_pivot = fc.pivot(index="city_name", columns="forecast_date", values="risk_score")
    fc_pivot.columns = [c.strftime("%a %d %b") for c in fc_pivot.columns]
    fig_fc = px.imshow(
        fc_pivot, aspect="auto", color_continuous_scale="OrRd", zmin=0, zmax=3,
        labels=dict(x="", y="", color="Risk score (0-3)"),
        title="Forecast risk score per city per day",
    )
    fig_fc.update_xaxes(tickmode="linear", dtick=1)
    st.plotly_chart(fig_fc, use_container_width=True)

    risky_fc = fc[fc["risk_score"] > 0].assign(day=lambda d: d["forecast_date"].dt.date)
    if risky_fc.empty:
        st.success("No risky days forecast for the selected cities. 🎉")
    else:
        st.markdown("**Upcoming risky days:**")
        st.dataframe(
            risky_fc[
                ["day", "city_name", "temp_max_celsius",
                 "precipitation_mm", "wind_gust_max_kmh", "risk_score"]
            ].rename(
                columns={
                    "city_name": "city",
                    "temp_max_celsius": "temp max °C",
                    "precipitation_mm": "precip mm",
                    "wind_gust_max_kmh": "gust km/h",
                    "risk_score": "risk (0-3)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.caption(
    "Models powering this dashboard: `fct_city_weather_day`, "
    "`fct_air_quality_city_day`, `dim_location`, `mart_heatwave_events`, "
    "`fct_weather_forecast_day`. "
    "Thresholds: AEMET Plan Meteoalerta (yellow warning) + European AQI."
)
