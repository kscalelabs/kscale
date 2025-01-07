"""Defines a unified client for the K-Scale WWW API."""

from kscale.web.clients.base import BaseClient
from kscale.web.clients.user import UserClient


class WWWClient(
    UserClient,
    BaseClient,
):
    pass
