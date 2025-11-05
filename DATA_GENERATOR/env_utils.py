"""Helpers for loading environment variables in different execution contexts."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from dotenv import load_dotenv

# Default search order covers running from the repo root or inside DATA_GENERATOR.
DEFAULT_ENV_PATHS: Sequence[Path] = (
    Path(".env"),
    Path("DATA_GENERATOR/.env"),
    Path("ARGO_CHATBOT/.env"),
    Path("../.env"),
)


def load_environment(paths: Iterable[Path] = DEFAULT_ENV_PATHS) -> None:
    """Attempt to load environment variables from the provided `.env` paths.

    The first existing file is loaded first, but later files are allowed to
    supplement values that were not already set to avoid surprising overrides.
    """
    loaded_any = False
    for candidate in paths:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            loaded_any = True
    if not loaded_any:
        # Fall back to a bare load in case dotenv can discover something else.
        load_dotenv()
