"""High-level routines orchestrating data refresh flows."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DATA_GENERATOR.config import REGION_LABEL
from DATA_GENERATOR.env_utils import load_environment
from DATA_GENERATOR.pipeline.db_loader import load_into_postgres
from DATA_GENERATOR.pipeline.netcdf_fetcher import fetch_netcdf_dataset
from DATA_GENERATOR.pipeline.netcdf_transformer import dataset_to_dataframe
from DATA_GENERATOR.pipeline.state_manager import load_last_success_timestamp, persist_last_success_timestamp


logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    requested_start: datetime
    requested_end: datetime
    downloaded_rows: int
    inserted_rows: int
    checkpoint_updated: bool
    actual_min_timestamp: Optional[datetime]
    actual_max_timestamp: Optional[datetime]
    unique_floats: int


def perform_update(
    progress_callback: Optional[Callable[[str], None]] = None,
    progress_step_callback: Optional[Callable[[int], None]] = None,
) -> UpdateResult:
    """Run the end-to-end update pipeline and return a structured summary."""
    load_environment()

    def log(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    def report(step: int) -> None:
        if progress_step_callback:
            progress_step_callback(step)

    last_success = load_last_success_timestamp()
    # Fetch an extra day to guard against late-arriving observations.
    fetch_start = (last_success - timedelta(days=1)).astimezone(timezone.utc)
    fetch_end = datetime.now(timezone.utc)

    if fetch_end <= fetch_start:
        fetch_end = fetch_start + timedelta(hours=1)

    report(0)
    log(f"🌊 Region: {REGION_LABEL}")
    log(f"📅 Requesting observations from {fetch_start.isoformat()} to {fetch_end.isoformat()} ...")
    log("🌐 Fetching NetCDF profiles from ERDDAP ...")

    dataset = fetch_netcdf_dataset(fetch_start, fetch_end)
    try:
        log("📦 Transforming NetCDF dataset into tabular records ...")
        dataframe = dataset_to_dataframe(dataset)
    finally:
        temp_path = dataset.attrs.pop("_local_temp_path", None)
        dataset.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug("Removed temporary NetCDF file: %s", temp_path)
            except OSError as exc:  # pragma: no cover - best effort cleanup
                logger.warning("Failed to remove temporary NetCDF file %s: %s", temp_path, exc)
    report(40)
    downloaded_rows = len(dataframe)
    if downloaded_rows == 0:
        log("ℹ️ No new records returned by ERDDAP.")
        report(100)
        return UpdateResult(
            requested_start=fetch_start,
            requested_end=fetch_end,
            downloaded_rows=0,
            inserted_rows=0,
            checkpoint_updated=False,
            actual_min_timestamp=None,
            actual_max_timestamp=None,
            unique_floats=0,
        )

    log(f"⬇️ Downloaded {downloaded_rows} rows.")

    total_rows, inserted_rows, _ = load_into_postgres(dataframe)
    log(f"🗄️ Prepared {total_rows} rows for database insertion.")
    log(f"✅ Inserted {inserted_rows} new rows into Postgres.")
    report(80)

    if inserted_rows > 0:
        persist_last_success_timestamp(fetch_end)
        log(f"🕒 Updated checkpoint to {fetch_end.isoformat()}.")
        checkpoint_updated = True
    else:
        checkpoint_updated = False
        log("ℹ️ Checkpoint unchanged because no rows were added.")

    min_ts = dataframe["timestamp"].min()
    max_ts = dataframe["timestamp"].max()
    unique_floats = dataframe["float_id"].nunique()
    report(100)

    return UpdateResult(
        requested_start=fetch_start,
        requested_end=fetch_end,
        downloaded_rows=downloaded_rows,
        inserted_rows=inserted_rows,
        checkpoint_updated=checkpoint_updated,
        actual_min_timestamp=min_ts if pd.notna(min_ts) else None,
        actual_max_timestamp=max_ts if pd.notna(max_ts) else None,
        unique_floats=unique_floats,
    )
