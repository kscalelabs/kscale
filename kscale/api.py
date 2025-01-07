"""Defines common functionality for the K-Scale API."""

from kscale.utils.api_base import APIBase
from kscale.web.api import WebAPI


class K(
    WebAPI,
    APIBase,
):
    """Defines a common interface for the K-Scale API."""
