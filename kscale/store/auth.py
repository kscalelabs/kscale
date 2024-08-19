"""Defines utility functions for authenticating the K-Scale Store API."""

from kscale.conf import Settings


def get_api_key() -> str:
    try:
        return Settings.load().store.api_key
    except AttributeError:
        raise ValueError(
            "API key not found! Get one here and set it as the `KSCALE_API_KEY` "
            "environment variable: https://kscale.store/keys"
        )
