"""Utility functions for interacting with the K-Scale Store API."""

import os

from kscale.conf import Settings

API_ROOT = "https://api.kscale.store"


def get_api_key() -> str:
    api_key = Settings.load().store.api_key
    if api_key is None:
        api_key = os.getenv("KSCALE_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found! Get one here and set it as the `KSCALE_API_KEY` environment variable or in your "
            "config file: https://kscale.store/keys"
        )
    return api_key
