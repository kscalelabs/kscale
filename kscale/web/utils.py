"""Utility functions for interacting with the K-Scale WWW API."""

import functools
import logging
from pathlib import Path

from kscale.conf import Settings

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_TIMEOUT = 300.0  # 5 minutes


@functools.lru_cache
def get_cache_dir() -> Path:
    """Returns the cache directory for artifacts."""
    return Path(Settings.load().www.cache_dir).expanduser().resolve()


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
