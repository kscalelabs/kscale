"""Defines the client for interacting with the K-Scale permission endpoints."""

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import PermissionResponse, UserPermissionsResponse


class PermissionClient(BaseClient):
    async def get_all_permissions(self) -> list[PermissionResponse]:
        """Get all available permissions."""
        data = await self._request("GET", "/permissions/list")
        return [PermissionResponse.model_validate(item) for item in data]

    async def get_user_permissions(self, user_id: str = "me") -> UserPermissionsResponse:
        """Get permissions for a specific user."""
        data = {"user_id": user_id}
        data = await self._request("GET", "/permissions/user", data=data, auth=True)
        return UserPermissionsResponse.model_validate(data)

    async def update_user_permissions(self, user_id: str, permissions: list[str]) -> UserPermissionsResponse:
        """Update permissions for a user."""
        data = {"user_id": user_id, "permissions": permissions}
        response_data = await self._request("PUT", "/permissions/user", data=data, auth=True)
        return UserPermissionsResponse.model_validate(response_data)

    async def add_user_permission(self, user_id: str, permission: str) -> UserPermissionsResponse:
        """Add a single permission to a user."""
        data = {"user_id": user_id, "permission": permission}
        response_data = await self._request("POST", "/permissions/user", data=data, auth=True)
        return UserPermissionsResponse.model_validate(response_data)

    async def remove_user_permission(self, user_id: str, permission: str) -> UserPermissionsResponse:
        """Remove a single permission from a user."""
        params = {"user_id": user_id, "permission": permission}
        response_data = await self._request("DELETE", "/permissions/user", params=params, auth=True)
        return UserPermissionsResponse.model_validate(response_data)
