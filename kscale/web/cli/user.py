"""Defines the CLI for getting information about the current user."""

import logging

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.user import UserClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Get information about the currently-authenticated user."""
    pass


@cli.command()
@coro
async def me() -> None:
    """Get information about the currently-authenticated user."""
    client = UserClient()
    profile = await client.get_profile_info()
    click.echo(
        tabulate(
            [
                ["Email", profile.email],
                ["Email verified", profile.email_verified],
                ["User ID", profile.user.user_id],
                ["Is admin", profile.user.is_admin],
                ["Can upload", profile.user.can_upload],
                ["Can test", profile.user.can_test],
            ],
            headers=["Key", "Value"],
            tablefmt="simple",
        )
    )


if __name__ == "__main__":
    cli()
