"""Defines the client for interacting with the K-Scale group endpoints."""

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import (
    GroupMembershipResponse,
    GroupResponse,
    GroupShareResponse,
)


class GroupClient(BaseClient):
    async def get_groups(self) -> list[GroupResponse]:
        """Get all groups for the authenticated user."""
        data = await self._request("GET", "/groups/", auth=True)
        return [GroupResponse.model_validate(item) for item in data]

    async def get_group(self, group_id: str) -> GroupResponse:
        """Get a specific group by ID."""
        data = await self._request("GET", f"/groups/{group_id}", auth=True)
        return GroupResponse.model_validate(data)

    async def create_group(self, name: str, description: str | None = None) -> GroupResponse:
        """Create a new group."""
        data = {"name": name}
        if description is not None:
            data["description"] = description
        response_data = await self._request("POST", "/groups/", data=data, auth=True)
        return GroupResponse.model_validate(response_data)

    async def update_group(
        self,
        group_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> GroupResponse:
        """Update a group's metadata."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        response_data = await self._request("POST", f"/groups/{group_id}", data=data, auth=True)
        return GroupResponse.model_validate(response_data)

    async def delete_group(self, group_id: str) -> None:
        """Delete a group."""
        await self._request("DELETE", f"/groups/{group_id}", auth=True)

    # Group membership management
    async def get_group_memberships(self, group_id: str) -> list[GroupMembershipResponse]:
        """Get all memberships for a group."""
        data = await self._request("GET", f"/groups/{group_id}/memberships", auth=True)
        return [GroupMembershipResponse.model_validate(item) for item in data]

    async def request_group_membership(self, group_id: str) -> GroupMembershipResponse:
        """Request to join a group."""
        data = await self._request("POST", f"/groups/{group_id}/memberships", auth=True)
        return GroupMembershipResponse.model_validate(data)

    async def approve_group_membership(self, group_id: str, user_id: str) -> GroupMembershipResponse:
        """Approve a membership request."""
        data = await self._request("POST", f"/groups/{group_id}/memberships/{user_id}/approve", auth=True)
        return GroupMembershipResponse.model_validate(data)

    async def reject_group_membership(self, group_id: str, user_id: str) -> None:
        """Reject a membership request."""
        await self._request("DELETE", f"/groups/{group_id}/memberships/{user_id}", auth=True)

    # Group sharing management
    async def get_group_shares(self, group_id: str) -> list[GroupShareResponse]:
        """Get all resources shared with a group."""
        data = await self._request("GET", f"/groups/{group_id}/shares", auth=True)
        return [GroupShareResponse.model_validate(item) for item in data]

    async def share_resource_with_group(
        self, group_id: str, resource_type: str, resource_id: str
    ) -> GroupShareResponse:
        """Share a resource with a group."""
        data = {"resource_type": resource_type, "resource_id": resource_id}
        response_data = await self._request("POST", f"/groups/{group_id}/shares", data=data, auth=True)
        return GroupShareResponse.model_validate(response_data)

    async def unshare_resource_from_group(self, group_id: str, share_id: str) -> None:
        """Remove a resource share from a group."""
        await self._request("DELETE", f"/groups/{group_id}/shares/{share_id}", auth=True)
