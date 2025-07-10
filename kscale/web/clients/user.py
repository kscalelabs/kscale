"""Defines the client for interacting with the K-Scale authentication endpoints."""

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import ProfileResponse


class UserClient(BaseClient):
    async def get_profile_info(self) -> ProfileResponse:
        data = await self._request("GET", "/auth/profile", auth=True)
        return ProfileResponse(**data)
