"""Defines common functionality for the K-Scale API."""

from kscale.store.api import StoreAPI
from kscale.utils.api_base import APIBase


class KScale(
    StoreAPI,
    APIBase,
):
    """Defines a common interface for the K-Scale API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
