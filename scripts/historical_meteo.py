import json
import ssl
import csv
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ctx = ssl.create_default_context()

CITIES = [
    {"name": "Madrid",    "latitude": 40.4168, "longitude": -3.7038, "timezone": "Europe/Madrid"},
    {"name": "Barcelona", "latitude": 41.3888, "longitude":  2.1590, "timezone": "Europe/Madrid"},
    {"name": "Valencia",  "latitude": 39.4699, "longitude": -0.3763, "timezone": "Europe/Madrid"},
    {"name": "Sevilla",   "latitude": 37.3886, "longitude": -5.9823, "timezone": "Europe/Madrid"},
    {"name": "Bilbao",    "latitude": 43.2630, "longitude": -2.9350, "timezone": "Europe/Madrid"},
]

all_rows = []

for city in CITIES:
    print(f"Fetching {city['name']}...")
    
    params = {
        "latitude":   city["latitude"],
        "longitude":  city["longitude"],
        "start_date": "2023-01-01",
        "end_date":   "2024-12-31",
        "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":   city["timezone"],
    }

    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "dbt-ie/1.0"})

    with urlopen(req, timeout=30, context=ctx) as r:
        data = json.loads(r.read())

    daily = data["daily"]
    for i, date in enumerate(daily["time"]):
        all_rows.append({
            "city_name":           city["name"],
            "date":                date,
            "temperature_2m_max":  daily["temperature_2m_max"][i],
            "temperature_2m_min":  daily["temperature_2m_min"][i],
            "precipitation_sum":   daily["precipitation_sum"][i],
        })

out = Path("data/raw/open_meteo/raw_historical_weather_daily.csv")
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Done — {len(all_rows)} rows written to {out}")