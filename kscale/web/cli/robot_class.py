"""Defines the CLI for getting information about robot classes."""

import logging

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.robot_class import RobotClassClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Get information about robot classes."""
    pass


@cli.command()
@coro
async def list() -> None:
    """Lists all robot classes."""
    client = RobotClassClient()
    robot_classes = await client.get_robot_classes()
    if robot_classes:
        # Prepare table data
        table_data = [
            [
                click.style(rc.id, fg="blue"),
                click.style(rc.class_name, fg="green"),
                rc.description or "N/A",
            ]
            for rc in robot_classes
        ]
        click.echo(tabulate(table_data, headers=["ID", "Name", "Description"], tablefmt="simple"))
    else:
        click.echo(click.style("No robot classes found", fg="red"))


@cli.command()
@click.argument("name")
@click.option("-d", "--description", type=str, default=None)
@coro
async def add(
    name: str,
    description: str | None = None,
) -> None:
    """Adds a new robot class."""
    async with RobotClassClient() as client:
        robot_class = await client.create_robot_class(name, description)
    click.echo("Robot class created:")
    click.echo(f"  ID: {click.style(robot_class.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot_class.class_name, fg='green')}")
    click.echo(f"  Description: {click.style(robot_class.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("current_name")
@click.option("-n", "--name", type=str, default=None)
@click.option("-d", "--description", type=str, default=None)
@coro
async def update(current_name: str, name: str | None = None, description: str | None = None) -> None:
    """Updates a robot class."""
    async with RobotClassClient() as client:
        robot_class = await client.update_robot_class(current_name, name, description)
    click.echo("Robot class updated:")
    click.echo(f"  ID: {click.style(robot_class.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot_class.class_name, fg='green')}")
    click.echo(f"  Description: {click.style(robot_class.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("name")
@coro
async def delete(name: str) -> None:
    """Deletes a robot class."""
    async with RobotClassClient() as client:
        await client.delete_robot_class(name)
    click.echo(f"Robot class deleted: {click.style(name, fg='red')}")


@cli.group()
def urdf() -> None:
    """Handle the robot class URDF."""
    pass


@urdf.command()
@click.argument("class_name")
@click.argument("urdf_file")
@coro
async def upload(class_name: str, urdf_file: str) -> None:
    """Uploads a URDF file to a robot class."""
    async with RobotClassClient() as client:
        response = await client.upload_robot_class_urdf(class_name, urdf_file)
    click.echo("URDF uploaded:")
    click.echo(f"  Filename: {click.style(response.filename, fg='green')}")


@urdf.command()
@click.argument("class_name")
@click.option("--no-cache", is_flag=True, default=False)
@coro
async def download(class_name: str, no_cache: bool) -> None:
    """Downloads a URDF file from a robot class."""
    async with RobotClassClient() as client:
        urdf_file = await client.download_robot_class_urdf(class_name, cache=not no_cache)
    click.echo(f"URDF downloaded: {click.style(urdf_file, fg='green')}")


if __name__ == "__main__":
    cli()
