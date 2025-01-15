"""Defines the CLI for interacting with K-Scale's OpenID Connect server."""

import logging

import click

from kscale.utils.cli import coro
from kscale.web.clients.base import BaseClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Retrieve an OICD token from the K-Scale authentication server."""
    pass


@cli.command()
@coro
async def get() -> None:
    """Get a bearer token from OpenID Connect."""
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    async with BaseClient() as client:
        try:
            token = await client.get_bearer_token()
            logger.info("Bearer token: %s", token)
        except Exception:
            logger.exception("Error getting bearer token")


if __name__ == "__main__":
    cli()
