"""Defines a unified client for the K-Scale WWW API."""

from kscale.web.clients.base import BaseClient
from kscale.web.clients.robot import RobotClient
from kscale.web.clients.robot_class import RobotClassClient
from kscale.web.clients.user import UserClient


class WWWClient(
    RobotClient,
    RobotClassClient,
    UserClient,
    BaseClient,
):
    pass
