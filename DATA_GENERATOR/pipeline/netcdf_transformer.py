"""Transform NetCDF datasets into cleaned pandas DataFrames."""
from __future__ import annotations

import os
import sys

import pandas as pd
import xarray as xr

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DATA_GENERATOR.config import CANONICAL_COLUMNS


def dataset_to_dataframe(dataset: xr.Dataset) -> pd.DataFrame:
    """Convert an ARGO NetCDF dataset into the canonical dataframe.

    The function flattens the multi-dimensional structure, keeps only the
    configured columns, and filters out rows failing the basic QC flags when
    available.
    """
    if dataset is None:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    df = dataset.to_dataframe().reset_index()

    # Normalize column names to match the canonical schema.
    rename_map = {
        "platform_number": "float_id",
        "time": "timestamp",
        "pres": "pressure",
        "temp": "temperature",
        "psal": "salinity",
        "chla": "chlorophyll",
        "doxy": "dissolved_oxygen",
    }
    df = df.rename(columns=rename_map)

    # Drop rows lacking essential coordinates or timestamp information.
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "float_id"])

    # Basic QC filtering when flags are present in the dataset.
    for variable in ("temp", "pres", "psal", "doxy", "chla"):
        qc_col = f"{variable}_qc"
        if qc_col in df.columns:
            df = df[~df[qc_col].astype(str).isin({"4", "9"})]

    # Ensure all expected columns exist.
    for column in CANONICAL_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df = df[CANONICAL_COLUMNS]

    df = df.drop_duplicates(subset=["float_id", "timestamp", "pressure"], keep="last")
    df = df.sort_values("timestamp").reset_index(drop=True)

    numeric_columns = [col for col in CANONICAL_COLUMNS if col not in {"timestamp"}]
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")

    return df
