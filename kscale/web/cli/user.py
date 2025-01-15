"""Defines the CLI for getting information about the current user."""

import logging

import click

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
    client = UserClient()
    profile = await client.get_profile_info()
    logger.info("Email: %s", profile.email)
    logger.info("Email verified: %s", profile.email_verified)
    logger.info("User ID: %s", profile.user.user_id)
    logger.info("Is admin: %s", profile.user.is_admin)
    logger.info("Can upload: %s", profile.user.can_upload)
    logger.info("Can test: %s", profile.user.can_test)


if __name__ == "__main__":
    cli()
