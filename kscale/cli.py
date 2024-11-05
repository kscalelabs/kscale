"""Defines the top-level KOL CLI."""

import click

from kscale.utils.cli import recursive_help
from kscale.web.pybullet import cli as pybullet_cli
from kscale.web.teleop import cli as teleop_cli
from kscale.web.urdf import cli as urdf_cli


@click.group()
def cli() -> None:
    """Command line interface for interacting with the K-Scale store."""
    pass


cli.add_command(urdf_cli, "urdf")
cli.add_command(pybullet_cli, "pybullet")
cli.add_command(teleop_cli, "teleop")

if __name__ == "__main__":
    # python -m kscale.cli
    print(recursive_help(cli))
