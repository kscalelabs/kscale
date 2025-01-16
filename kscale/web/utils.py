"""Utility functions for interacting with the K-Scale WWW API."""

import functools
import logging
import time
from pathlib import Path

from kscale.conf import Settings

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_TIMEOUT = 300.0  # 5 minutes


@functools.lru_cache
def get_cache_dir() -> Path:
    """Returns the cache directory for artifacts."""
    return Path(Settings.load().www.cache_dir).expanduser().resolve()


def should_refresh_file(file: Path) -> bool:
    """Returns whether the file should be refreshed."""
    return file.exists() and file.stat().st_mtime < time.time() - Settings.load().www.refresh_interval_minutes * 60


@functools.lru_cache
def get_artifact_dir(artifact_id: str) -> Path:
    """Returns the directory for a specific artifact."""
    cache_dir = get_cache_dir() / artifact_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@functools.lru_cache
def get_api_root() -> str:
    """Returns the root URL for the K-Scale WWW API."""
    return Settings.load().www.api_root
