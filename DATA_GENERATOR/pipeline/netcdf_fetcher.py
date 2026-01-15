"""Utility functions to download ARGO observations from ERDDAP servers."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable

import pandas as pd
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DATA_GENERATOR.config import (
    LATITUDE_RANGE,
    LONGITUDE_RANGE,
    REQUEST_TIMEOUT,
)

# ERDDAP servers - primary and fallback
ERDDAP_SERVERS = [
    {
        "name": "Ifremer",
        "base_url": "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.json",
    },
    {
        "name": "NOAA PMEL",
        "base_url": "https://data.pmel.noaa.gov/pmel/erddap/tabledap/ARGO.json",
    }
]


def fetch_argo_data(
    start: datetime,
    end: datetime,
    progress_callback: Optional[Callable[[str], None]] = None
) -> pd.DataFrame:
    """Download ARGO float data from ERDDAP servers for the given time range.
    
    Parameters
    ----------
    start : datetime
        Inclusive start timestamp (UTC).
    end : datetime
        Inclusive end timestamp (UTC).
    progress_callback : callable, optional
        Function to call with status updates.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: float_id, timestamp, latitude, longitude, 
        pressure, temperature, salinity, dissolved_oxygen, chlorophyll
    """
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    # Ensure UTC timezone
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
        
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    
    lat_min, lat_max = LATITUDE_RANGE
    lon_min, lon_max = LONGITUDE_RANGE
    
    # Format dates for ERDDAP query
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    log(f"📅 Date range: {start_str} to {end_str}")
    log(f"📍 Region: {lat_min}° to {lat_max}° lat, {lon_min}° to {lon_max}° lon")
    
    # Try each server
    for server in ERDDAP_SERVERS:
        server_name = server["name"]
        base_url = server["base_url"]
        
        log(f"🌐 Trying {server_name} ERDDAP server...")
        
        try:
            # Build ERDDAP query URL
            # Request: platform_number, time, latitude, longitude, pres, temp, psal
            query = (
                f"?platform_number,time,latitude,longitude,pres,temp,psal"
                f"&time>={start_str}"
                f"&time<={end_str}"
                f"&latitude>={lat_min}"
                f"&latitude<={lat_max}"
                f"&longitude>={lon_min}"
                f"&longitude<={lon_max}"
                f"&orderBy(%22time%22)"
            )
            
            url = base_url + query
            log(f"🔗 Requesting data...")
            
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 404:
                log(f"⚠️ No data found on {server_name}")
                continue
            
            response.raise_for_status()
            data = response.json()
            
            # Parse ERDDAP JSON response
            table = data.get("table", {})
            column_names = table.get("columnNames", [])
            rows = table.get("rows", [])
            
            log(f"✅ Received {len(rows)} records from {server_name}")
            
            if not rows:
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Rename columns to match our schema
            column_mapping = {
                "platform_number": "float_id",
                "time": "timestamp",
                "pres": "pressure",
                "temp": "temperature",
                "psal": "salinity",
            }
            df = df.rename(columns=column_mapping)
            
            # Add missing columns
            if "dissolved_oxygen" not in df.columns:
                df["dissolved_oxygen"] = None
            if "chlorophyll" not in df.columns:
                df["chlorophyll"] = None
            
            # Convert timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            
            # Convert numeric columns
            numeric_cols = ["latitude", "longitude", "pressure", "temperature", "salinity"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Filter out rows with no temperature or salinity
            df = df.dropna(subset=["temperature", "salinity"], how="all")
            
            # Ensure column order
            output_cols = [
                "float_id", "timestamp", "latitude", "longitude",
                "pressure", "temperature", "salinity", "dissolved_oxygen", "chlorophyll"
            ]
            df = df[[c for c in output_cols if c in df.columns]]
            
            log(f"📊 Processed {len(df)} valid measurements")
            
            return df
            
        except requests.exceptions.Timeout:
            log(f"⏱️ Timeout on {server_name}, trying next server...")
            continue
        except requests.exceptions.RequestException as e:
            log(f"❌ Error on {server_name}: {e}")
            continue
        except Exception as e:
            log(f"❌ Failed to parse {server_name} response: {e}")
            continue
    
    # All servers failed
    log("❌ All ERDDAP servers failed. Please try again later.")
    return pd.DataFrame()


def fetch_argo_data_chunked(
    start: datetime,
    end: datetime,
    chunk_days: int = 7,
    progress_callback: Optional[Callable[[str], None]] = None
) -> pd.DataFrame:
    """Download ARGO data in chunks to handle large date ranges.
    
    Parameters
    ----------
    start : datetime
        Start date.
    end : datetime
        End date.
    chunk_days : int
        Number of days per chunk.
    progress_callback : callable, optional
        Progress callback function.
        
    Returns
    -------
    pd.DataFrame
        Combined DataFrame from all chunks.
    """
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    all_dfs = []
    current = start
    chunk_num = 0
    total_days = (end - start).days
    num_chunks = (total_days // chunk_days) + 1
    
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        chunk_num += 1
        
        log(f"📦 Fetching chunk {chunk_num}/{num_chunks}: {current.date()} to {chunk_end.date()}")
        
        df = fetch_argo_data(current, chunk_end, progress_callback)
        
        if not df.empty:
            all_dfs.append(df)
            log(f"✅ Chunk {chunk_num}: {len(df)} records")
        
        current = chunk_end + timedelta(days=1)
    
    if all_dfs:
        result = pd.concat(all_dfs, ignore_index=True)
        # Remove duplicates based on float_id, timestamp, pressure
        result = result.drop_duplicates(subset=["float_id", "timestamp", "pressure"])
        log(f"📊 Total: {len(result)} unique records")
        return result
    
    return pd.DataFrame()
