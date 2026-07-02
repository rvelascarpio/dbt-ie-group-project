#!/usr/bin/env python3
"""Extract ONLY the missing raw_weather_daily.csv (recent daily weather).

Same logic as the teacher's extract_open_meteo.py, trimmed to just the
"recent weather" part (Forecast API with past_days). Writes one file:

    data/raw/open_meteo/raw_weather_daily.csv

It does NOT touch the other CSVs. Run it from the project root:

    uv run python scripts/extract_weather_daily.py
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_CITIES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"]
DEFAULT_DAILY_WEATHER_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "wind_speed_10m_max",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract recent daily weather (raw_weather_daily.csv) from Open-Meteo."
    )
    parser.add_argument("--cities", nargs="+", default=DEFAULT_CITIES)
    parser.add_argument(
        "--past-days",
        type=int,
        default=30,
        help="Number of recent past days to extract from the Forecast API. Maximum is 92.",
    )
    parser.add_argument("--output-dir", default="data/raw/open_meteo")
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    args = parser.parse_args()
    if not 0 <= args.past_days <= 92:
        parser.error("--past-days must be between 0 and 92.")
    return args


def get_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query_string = urlencode(params, doseq=True)
    request = Request(
        f"{url}?{query_string}",
        headers={"User-Agent": "dbt-ie-open-meteo-assignment/1.0"},
    )
    with urlopen(request, timeout=30, context=get_ssl_context()) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def geocode_city(city: str) -> dict[str, Any]:
    data = get_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No geocoding result found for city: {city}")
    result = results[0]
    return {
        "location_id": result.get("id"),
        "city_name": result.get("name"),
        "country_code": result.get("country_code"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),
    }


def build_daily_rows(
    payload: dict[str, Any],
    location: dict[str, Any],
    extracted_at: str,
    source_name: str,
) -> list[dict[str, Any]]:
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    rows = []
    for index, day in enumerate(dates):
        row = {
            "source_name": source_name,
            "extracted_at": extracted_at,
            "location_id": location["location_id"],
            "city_name": location["city_name"],
            "country_code": location["country_code"],
            "date": day,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "timezone": payload.get("timezone"),
        }
        for variable, values in daily.items():
            if variable == "time":
                continue
            row[variable] = values[index]
        rows.append(row)
    return rows


def fetch_recent_weather(
    location: dict[str, Any], past_days: int, extracted_at: str
) -> list[dict[str, Any]]:
    payload = get_json(
        FORECAST_URL,
        {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "past_days": past_days,
            "forecast_days": 1,
            "daily": ",".join(DEFAULT_DAILY_WEATHER_VARIABLES),
            "timezone": location["timezone"] or "auto",
        },
    )
    return build_daily_rows(payload, location, extracted_at, "recent_weather")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    extracted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    weather_daily_rows = []
    for city in args.cities:
        print(f"Extracting {city}...", file=sys.stderr)
        location = geocode_city(city)
        time.sleep(args.pause_seconds)
        weather_daily_rows.extend(
            fetch_recent_weather(location, args.past_days, extracted_at)
        )
        time.sleep(args.pause_seconds)

    out = output_dir / "raw_weather_daily.csv"
    write_csv(out, weather_daily_rows)
    print(f"Wrote {len(weather_daily_rows):,} rows to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
