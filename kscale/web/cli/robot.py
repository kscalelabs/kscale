"""Defines the CLI for getting information about robots."""

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.robot import RobotClient


@click.group()
def cli() -> None:
    """Get information about robots."""
    pass


@cli.command()
@coro
async def list() -> None:
    client = RobotClient()
    robots = await client.get_all_robots()
    if robots:
        table_data = [
            [
                click.style(robot.id, fg="blue"),
                click.style(robot.robot_name, fg="green"),
                click.style(robot.class_id, fg="yellow"),
                robot.description or "N/A",
            ]
            for robot in robots
        ]
        click.echo(tabulate(table_data, headers=["ID", "Name", "Class", "Description"], tablefmt="simple"))
    else:
        click.echo(click.style("No robots found", fg="red"))


@cli.command()
@click.option("-u", "--user-id", type=str, default="me")
@coro
async def user(user_id: str = "me") -> None:
    client = RobotClient()
    robots = await client.get_user_robots(user_id)
    if robots:
        table_data = [
            [
                click.style(robot.id, fg="blue"),
                click.style(robot.robot_name, fg="green"),
                click.style(robot.class_id, fg="yellow"),
                robot.description or "N/A",
            ]
            for robot in robots
        ]
        click.echo(tabulate(table_data, headers=["ID", "Name", "Class", "Description"], tablefmt="simple"))
    else:
        click.echo(click.style("No robots found", fg="red"))


@cli.command()
@click.argument("robot_id")
@coro
async def id(robot_id: str) -> None:
    client = RobotClient()
    robot = await client.get_robot_by_id(robot_id)
    click.echo("Robot:")
    click.echo(f"  ID: {click.style(robot.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot.robot_name, fg='green')}")
    click.echo(f"  Class: {click.style(robot.class_name, fg='yellow')}")
    click.echo(f"  Description: {click.style(robot.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("robot_name")
@coro
async def name(robot_name: str) -> None:
    client = RobotClient()
    robot = await client.get_robot_by_name(robot_name)
    click.echo("Robot:")
    click.echo(f"  ID: {click.style(robot.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot.robot_name, fg='green')}")
    click.echo(f"  Class: {click.style(robot.class_name, fg='yellow')}")
    click.echo(f"  Description: {click.style(robot.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("class_name")
@click.argument("name")
@click.option("-c", "--class-name", type=str, required=True)
@click.option("-d", "--description", type=str, default=None)
@coro
async def add(name: str, class_name: str, description: str | None = None) -> None:
    client = RobotClient()
    robot = await client.add_robot(name, class_name, description)
    click.echo("Robot added:")
    click.echo(f"  ID: {click.style(robot.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot.robot_name, fg='green')}")
    click.echo(f"  Class: {click.style(robot.class_name, fg='yellow')}")
    click.echo(f"  Description: {click.style(robot.description or 'N/A', fg='yellow')}")


if __name__ == "__main__":
    cli()
