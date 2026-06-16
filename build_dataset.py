
from __future__ import annotations

import argparse
import os
from pathlib import Path

import holidays
import openmeteo_requests
import pandas as pd
import requests_cache
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from retry_requests import retry


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DEFAULT_COUNTRY_CODE = "DE_LU"
DEFAULT_LATITUDE = 52.52
DEFAULT_LONGITUDE = 13.41
DEFAULT_TIMEZONE = "Europe/Berlin"


def month_windows(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cursor = start
    while cursor < end:
        next_month = (cursor + pd.offsets.MonthBegin(1)).normalize()
        window_end = min(next_month, end)
        windows.append((cursor, window_end))
        cursor = window_end
    return windows


def normalize_series(series, name, timezone):
    if series is None or len(series) == 0:
        return pd.DataFrame(columns=["timestamp", name])

    # ENTSO-E may return either a Series or a DataFrame
    if isinstance(series, pd.DataFrame):
        if series.shape[1] == 1:
            frame = series.copy()
            frame.columns = [name]
        else:
            # If multiple columns are returned, use the first numeric column
            numeric_cols = series.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                frame = series[[numeric_cols[0]]].copy()
            else:
                frame = series.iloc[:, [0]].copy()
            frame.columns = [name]
    else:
        frame = series.rename(name).to_frame()

    frame.index = pd.to_datetime(frame.index)

    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")

    frame = frame.tz_convert(timezone)
    frame = frame.reset_index().rename(columns={"index": "timestamp"})

    return frame


def fetch_entsoe_load(
    api_key: str,
    country_code: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    timezone: str,
) -> pd.DataFrame:
    client = EntsoePandasClient(api_key=api_key)
    actual_parts: list[pd.DataFrame] = []
    forecast_parts: list[pd.DataFrame] = []

    for window_start, window_end in month_windows(start, end):
        actual = client.query_load(country_code, start=window_start, end=window_end)
        forecast = client.query_load_forecast(country_code, start=window_start, end=window_end)
        actual_parts.append(normalize_series(actual, "load_mw", timezone))
        forecast_parts.append(normalize_series(forecast, "load_forecast_mw", timezone))

    actual_load = pd.concat(actual_parts)
    forecast_load = pd.concat(forecast_parts)
    actual_load = actual_load.loc[~actual_load.index.duplicated(keep="first")]
    forecast_load = forecast_load.loc[~forecast_load.index.duplicated(keep="first")]
    return (
    pd.merge(
        actual_load,
        forecast_load,
        on="timestamp",
        how="outer"
    )
    .sort_values("timestamp")
    .reset_index(drop=True)
)


def fetch_open_meteo(
    start: pd.Timestamp,
    end: pd.Timestamp,
    latitude: float,
    longitude: float,
    timezone: str,
) -> pd.DataFrame:
    cache_session = requests_cache.CachedSession(str(PROJECT_ROOT / ".cache" / "openmeteo"), expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    client = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.date().isoformat(),
        "end_date": (end - pd.Timedelta(days=1)).date().isoformat(),
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "timezone": timezone,
    }
    response = client.weather_api("https://archive-api.open-meteo.com/v1/archive", params=params)[0]
    hourly = response.Hourly()

    index = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True).tz_convert(timezone),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True).tz_convert(timezone),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    return pd.DataFrame(
        {
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
        },
        index=index,
    )


def add_features(frame: pd.DataFrame, country_code: str) -> pd.DataFrame:
    dataset = frame.copy()
    dataset["hour"] = dataset.index.hour
    dataset["dayofweek"] = dataset.index.dayofweek
    dataset["month"] = dataset.index.month
    dataset["is_weekend"] = dataset["dayofweek"].isin([5, 6]).astype(int)

    holiday_country = country_code.split("_")[0]
    holiday_dates = holidays.country_holidays(holiday_country)
    dataset["is_holiday"] = [int(ts.date() in holiday_dates) for ts in dataset.index]

    dataset["load_lag_24h"] = dataset["load_mw"].shift(24)
    dataset["load_lag_168h"] = dataset["load_mw"].shift(168)
    dataset["load_rolling_24h_mean"] = dataset["load_mw"].shift(1).rolling(24).mean()
    return dataset


def build_dataset(args: argparse.Namespace) -> Path:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = args.api_key or os.getenv("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError("ENTSOE_API_KEY가 없습니다. .env 파일이나 --api-key 옵션으로 토큰을 넣어주세요.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start, tz=args.timezone)
    end = pd.Timestamp(args.end, tz=args.timezone) + pd.Timedelta(days=1)

    load_frame = fetch_entsoe_load(api_key, args.country_code, start, end, args.timezone)
    weather_frame = fetch_open_meteo(start, end, args.latitude, args.longitude, args.timezone)

    load_frame.to_csv(RAW_DIR / "entsoe_load.csv", index_label="timestamp")
    weather_frame.to_csv(RAW_DIR / "open_meteo_weather.csv", index_label="timestamp")
    
    if "timestamp" in load_frame.columns:
        load_frame["timestamp"] = pd.to_datetime(load_frame["timestamp"])
        load_frame = load_frame.set_index("timestamp").sort_index()
    else:
        load_frame.index = pd.to_datetime(load_frame.index)
        load_frame = load_frame.sort_index()
    
    if "timestamp" in weather_frame.columns:
        weather_frame["timestamp"] = pd.to_datetime(weather_frame["timestamp"])
        weather_frame = weather_frame.set_index("timestamp").sort_index()
    else:
        weather_frame.index = pd.to_datetime(weather_frame.index)
        weather_frame = weather_frame.sort_index()
    
    dataset = load_frame.resample("h").mean().join(weather_frame.resample("h").mean(), how="left")
    dataset = add_features(dataset, args.country_code)
    dataset = dataset.dropna(subset=["load_mw"]).sort_index()

    output_path = PROCESSED_DIR / "power_load_dataset.csv"
    dataset.to_csv(output_path, index_label="timestamp")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a power-load forecasting dataset from ENTSO-E and Open-Meteo.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2023-01-01")
    parser.add_argument("--end", required=True, help="End date, inclusive, e.g. 2025-12-31")
    parser.add_argument("--country-code", default=DEFAULT_COUNTRY_CODE, help="ENTSO-E country/bidding-zone code")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--latitude", type=float, default=DEFAULT_LATITUDE)
    parser.add_argument("--longitude", type=float, default=DEFAULT_LONGITUDE)
    parser.add_argument("--api-key", default=None, help="ENTSO-E API key. Defaults to ENTSOE_API_KEY env var.")
    return parser.parse_args()


if __name__ == "__main__":
    output = build_dataset(parse_args())
    print(f"Dataset written to {output}")
