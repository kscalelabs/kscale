"""Utility functions for interacting with the K-Scale Store API."""

import os

from kscale.conf import Settings


def get_api_root() -> str:
    """Returns the base URL for the K-Scale Store API.

    This can be overridden when targetting a different server.

    Returns:
        The base URL for the K-Scale Store API.
    """
    return os.getenv("KSCALE_API_ROOT", "https://api.kscale.dev")


def get_api_key() -> str:
    """Returns the API key for the K-Scale Store API.

    Returns:
        The API key for the K-Scale Store API.
    """
    api_key = Settings.load().store.api_key
    if api_key is None:
        api_key = os.getenv("KSCALE_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found! Get one here and set it as the `KSCALE_API_KEY` environment variable or in your "
            "config file: https://kscale.store/keys"
        )
    return api_key
