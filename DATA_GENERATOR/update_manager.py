"""High-level routines orchestrating data refresh flows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import pandas as pd
from dotenv import load_dotenv

from config import REGION_LABEL
from csv_archive import append_to_archive
from data_fetcher import fetch_incremental_dataframe
from db_loader import load_into_postgres
from state_manager import load_last_success_timestamp, persist_last_success_timestamp


@dataclass
class UpdateResult:
    requested_start: datetime
    requested_end: datetime
    downloaded_rows: int
    inserted_rows: int
    archive_created: bool
    actual_min_timestamp: Optional[datetime]
    actual_max_timestamp: Optional[datetime]
    unique_floats: int


def perform_update(
    progress_callback: Optional[Callable[[str], None]] = None,
    progress_step_callback: Optional[Callable[[int], None]] = None,
) -> UpdateResult:
    """Run the end-to-end update pipeline and return a structured summary."""
    load_dotenv()

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

    dataframe = fetch_incremental_dataframe(fetch_start, fetch_end)
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
            archive_created=False,
            actual_min_timestamp=None,
            actual_max_timestamp=None,
            unique_floats=0,
        )

    log(f"⬇️ Downloaded {downloaded_rows} rows.")

    total_rows, inserted_rows, inserted_df = load_into_postgres(dataframe)
    log(f"🗄️ Prepared {total_rows} rows for database insertion.")
    log(f"✅ Inserted {inserted_rows} new rows into Postgres.")
    report(80)

    if inserted_rows > 0:
        archive_rows, created = append_to_archive(inserted_df)
        log("💾 Created archive file." if created else f"💾 Appended {archive_rows} rows to archive.")
        persist_last_success_timestamp(fetch_end)
        log(f"🕒 Updated checkpoint to {fetch_end.isoformat()}.")
    else:
        archive_rows, created = 0, False
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
        archive_created=created,
        actual_min_timestamp=min_ts if pd.notna(min_ts) else None,
        actual_max_timestamp=max_ts if pd.notna(max_ts) else None,
        unique_floats=unique_floats,
    )
