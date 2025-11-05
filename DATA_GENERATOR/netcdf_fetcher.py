"""Utility functions to download ARGO observations from ERDDAP as NetCDF."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from typing import Tuple

import requests
import xarray as xr

from config import (
    DATASET_ID,
    ERDDAP_BASE_URL,
    LATITUDE_RANGE,
    LONGITUDE_RANGE,
    PRESSURE_RANGE,
    REQUEST_TIMEOUT,
)


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


def build_erddap_url(start: datetime, end: datetime) -> str:
    """Construct the ERDDAP NetCDF query URL for the configured dataset and region."""
    start_utc = start.astimezone(timezone.utc).replace(microsecond=0)
    end_utc = end.astimezone(timezone.utc).replace(microsecond=0)
    start_iso = start_utc.isoformat().replace("+00:00", "Z")
    end_iso = end_utc.isoformat().replace("+00:00", "Z")
    lat_min, lat_max = LATITUDE_RANGE
    lon_min, lon_max = LONGITUDE_RANGE
    pres_min, pres_max = PRESSURE_RANGE
    variables = ",".join(VARIABLES)
    query = (
        f"time>={start_iso}&time<={end_iso}"
        f"&latitude>={lat_min}&latitude<={lat_max}"
        f"&longitude>={lon_min}&longitude<={lon_max}"
        f"&pres>={pres_min}&pres<={pres_max}"
    )
    return f"{ERDDAP_BASE_URL}{DATASET_ID}.nc?{variables}&{query}"


def fetch_netcdf_dataset(start: datetime, end: datetime) -> xr.Dataset:
    """Download a NetCDF dataset from ERDDAP for the given time range.

    Parameters
    ----------
    start : datetime
        Inclusive start timestamp (UTC).
    end : datetime
        Inclusive end timestamp (UTC).

    Returns
    -------
    xr.Dataset
        The downloaded dataset ready for further processing.
    """
    url = build_erddap_url(start, end)
    # Download to a temporary file because xarray struggles with ERDDAP constraints
    # when opening remote NetCDF resources directly.
    response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                tmp.write(chunk)
        temp_path = tmp.name

    try:
        dataset = xr.open_dataset(temp_path)
    except Exception:
        os.remove(temp_path)
        raise

    dataset.attrs["_local_temp_path"] = temp_path
    return dataset
