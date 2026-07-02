"""Load the raw Open-Meteo CSV files into a DuckDB database as tables.

This is the group-project equivalent of the class `create_db.py` (same name, same
role). The class version reads Parquet files; ours reads the CSVs the extraction
scripts produced.

Each CSV in `data/raw/open_meteo/` becomes one table in DuckDB. The leading
`raw_` prefix is stripped from the file name so the tables are named, e.g.,
`historical_weather_daily`, `locations`, `air_quality_hourly`. Those table names
are what `models/sources.yml` registers as the `raw` source, so dbt can read them
via `{{ source('raw', 'historical_weather_daily') }}`.

Run it before `dbt build`:

    uv run python create_db.py
"""

import argparse
from pathlib import Path

import duckdb

RAW_DIR = "data/raw/open_meteo"


def create_database(db_path: str, data_dir: str = RAW_DIR) -> None:
    """Create and populate a DuckDB database from every CSV file in `data_dir`."""
    data_path = Path(data_dir)
    csv_files = sorted(data_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_path.resolve()}")

    conn = duckdb.connect(db_path)
    try:
        for csv in csv_files:
            # raw_historical_weather_daily.csv -> historical_weather_daily
            table_name = csv.stem.removeprefix("raw_")
            conn.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS "
                "SELECT * FROM read_csv_auto(?, header=true)",
                [str(csv)],
            )
            print(f"Created table: {table_name}  (from {csv.name})")
    finally:
        conn.close()

    print(f"Database written to {Path(db_path).resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create and populate a DuckDB database from the raw Open-Meteo CSVs."
    )
    parser.add_argument(
        "--database",
        "-d",
        default="my_database",
        help="Name of the database file (without .duckdb extension). Default: my_database",
    )
    args = parser.parse_args()
    create_database(f"{args.database}.duckdb")
