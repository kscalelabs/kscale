"""Defines the top-level KOL CLI."""

import logging

import click
import colorlogging

from kscale.utils.cli import recursive_help
from kscale.web.cli.robot import cli as robot_cli
from kscale.web.cli.robot_class import cli as robot_class_cli
from kscale.web.cli.user import cli as user_cli


@click.group()
def cli() -> None:
    """Command line interface for interacting with the K-Scale web API."""
    colorlogging.configure()

    # Suppress aiohttp access logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


cli.add_command(user_cli, "user")
cli.add_command(robot_class_cli, "robots")
cli.add_command(robot_cli, "robot")

if __name__ == "__main__":
    # python -m kscale.cli
    print(recursive_help(cli))
