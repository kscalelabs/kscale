"""Defines the client for interacting with the K-Scale robot endpoints."""

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import Robot, RobotResponse


class RobotClient(BaseClient):
    async def get_all_robots(self) -> list[Robot]:
        data = await self._request("GET", "/robot/", auth=True)
        return [Robot.model_validate(item) for item in data]

    async def get_user_robots(self, user_id: str = "me") -> list[Robot]:
        data = await self._request("GET", f"/robot/user/{user_id}", auth=True)
        return [Robot.model_validate(item) for item in data]

    async def add_robot(
        self,
        robot_name: str,
        class_name: str,
        description: str | None = None,
    ) -> RobotResponse:
        data = {"class_name": class_name}
        if description is not None:
            data["description"] = description
        response = await self._request(
            "PUT",
            f"/robot/{robot_name}",
            data=data,
            auth=True,
        )
        return RobotResponse.model_validate(response)

    async def get_robot_by_id(self, robot_id: str) -> RobotResponse:
        data = await self._request("GET", f"/robot/id/{robot_id}", auth=True)
        return RobotResponse.model_validate(data)

    async def get_robot_by_name(self, robot_name: str) -> RobotResponse:
        data = await self._request("GET", f"/robot/name/{robot_name}", auth=True)
        return RobotResponse.model_validate(data)
