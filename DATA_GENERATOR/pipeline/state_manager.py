"""State management helpers for tracking update progress."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DATA_GENERATOR.config import DEFAULT_START_DATE, STATE_FILE_PATH


def _state_file() -> Path:
    return Path(STATE_FILE_PATH)


def load_last_success_timestamp() -> datetime:
    """Return the most recent successful update timestamp in UTC."""
    state_path = _state_file()
    if not state_path.exists():
        return DEFAULT_START_DATE

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        raw_value: Optional[str] = data.get("last_success_iso")
        if not raw_value:
            return DEFAULT_START_DATE
        return datetime.fromisoformat(raw_value).astimezone(timezone.utc)
    except (json.JSONDecodeError, ValueError):
        return DEFAULT_START_DATE


def persist_last_success_timestamp(ts: datetime) -> None:
    """Persist the supplied timestamp as the most recent successful update."""
    ts_utc = ts.astimezone(timezone.utc)
    payload = {"last_success_iso": ts_utc.isoformat()}
    _state_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")
