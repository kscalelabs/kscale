"""Defines the base class for the K-Scale API."""

import functools

from kscale.web.token import get_bearer_token


class APIBase:
    def __init__(self) -> None:
        pass

    @functools.lru_cache
    async def bearer_token(self) -> str:
        return await get_bearer_token()
