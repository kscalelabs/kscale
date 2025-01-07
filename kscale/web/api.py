"""Defines a common interface for the K-Scale WWW API."""

from kscale.utils.api_base import APIBase
from kscale.web.clients.client import WWWClient
from kscale.web.gen.api import ProfileResponse


class WebAPI(APIBase):
    async def www_client(self) -> WWWClient:
        return WWWClient()

    async def get_profile_info(self) -> ProfileResponse:
        client = await self.www_client()
        return await client.get_profile_info()
