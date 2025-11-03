"""Utility helpers for maintaining the local CSV archive."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

from config import CANONICAL_COLUMNS, CSV_ARCHIVE_PATH


def append_to_archive(df: pd.DataFrame) -> Tuple[int, bool]:
    """Persist new observations onto the CSV archive, creating it if missing."""
    if df.empty:
        return 0, False

    archive_path = Path(CSV_ARCHIVE_PATH)
    exists = archive_path.exists()

    df_to_write = df[CANONICAL_COLUMNS]
    df_to_write.to_csv(
        archive_path,
        mode="a" if exists else "w",
        header=not exists,
        index=False,
    )
    return len(df_to_write), not exists
