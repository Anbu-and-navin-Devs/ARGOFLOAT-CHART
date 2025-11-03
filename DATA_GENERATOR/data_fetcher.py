"""Functions for fetching incremental ARGO data from ERDDAP."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pandas as pd
import requests

from config import (
    CANONICAL_COLUMNS,
    DATASET_ID,
    LATITUDE_RANGE,
    LONGITUDE_RANGE,
    PRESSURE_RANGE,
    REQUEST_TIMEOUT,
)

# Mapping returned ERDDAP columns to our canonical schema.
COLUMN_RENAME_MAP: Dict[str, str] = {
    "platform_number": "float_id",
    "PLATFORM_NUMBER": "float_id",
    "time": "timestamp",
    "time (UTC)": "timestamp",
    "TIME": "timestamp",
    "latitude": "latitude",
    "LATITUDE": "latitude",
    "latitude (degrees_north)": "latitude",
    "longitude": "longitude",
    "LONGITUDE": "longitude",
    "longitude (degrees_east)": "longitude",
    "pres": "pressure",
    "PRES": "pressure",
    "pres (decibar)": "pressure",
    "temp": "temperature",
    "TEMP": "temperature",
    "temp (degree_Celsius)": "temperature",
    "psal": "salinity",
    "PSAL": "salinity",
    "psal (PSU)": "salinity",
    "psal (psu)": "salinity",
    "chla": "chlorophyll",
    "CHLA": "chlorophyll",
    "chla (mg m-3)": "chlorophyll",
    "chla (mg/m3)": "chlorophyll",
    "doxy": "dissolved_oxygen",
    "DOXY": "dissolved_oxygen",
    "doxy (micromole kg-1)": "dissolved_oxygen",
    "doxy (micromole/kg)": "dissolved_oxygen",
}

VARIABLES: Tuple[str, ...] = (
    "platform_number",
    "time",
    "latitude",
    "longitude",
    "pres",
    "temp",
    "psal",
    "chla",
    "doxy",
)


def _build_query(start: datetime, end: datetime) -> str:
    start_iso = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    end_iso = end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    lat_min, lat_max = LATITUDE_RANGE
    lon_min, lon_max = LONGITUDE_RANGE
    pres_min, pres_max = PRESSURE_RANGE
    return (
        f"&time>={start_iso}&time<={end_iso}"
        f"&latitude>={lat_min}&latitude<={lat_max}"
        f"&longitude>={lon_min}&longitude<={lon_max}"
        f"&pres>={pres_min}&pres<={pres_max}"
    )


def fetch_incremental_dataframe(start: datetime, end: datetime) -> pd.DataFrame:
    """Retrieve ARGO observations for the given window and normalize columns."""
    base_url = f"https://erddap.ifremer.fr/erddap/tabledap/{DATASET_ID}.csvp"
    variable_segment = ",".join(VARIABLES)
    query_segment = _build_query(start, end)
    request_url = f"{base_url}?{variable_segment}{query_segment}"

    response = requests.get(request_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    # ERDDAP returns an extra header row describing the dataset; skip it.
    df = pd.read_csv(io.StringIO(response.text), skiprows=[1], low_memory=False)
    if df.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    df = df.rename(columns=COLUMN_RENAME_MAP)

    # Keep only the canonical columns we understand.
    usable_columns = [col for col in CANONICAL_COLUMNS if col in df.columns]
    df = df[usable_columns]

    # Ensure all expected columns exist even if empty.
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[CANONICAL_COLUMNS]

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "float_id"])
    df = df.drop_duplicates(subset=["float_id", "timestamp", "pressure"], keep="last")

    numeric_columns: List[str] = [
        col
        for col in CANONICAL_COLUMNS
        if col not in {"timestamp"}
    ]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
