"""Defines the CLI for interacting with K-Scale's OpenID Connect server."""

import logging

import click

from kscale.utils.cli import coro
from kscale.web.token import get_bearer_token

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """K-Scale OpenID Connect CLI tool."""
    pass


@cli.command()
@click.option("--no-cache", is_flag=True, help="Do not use the cached bearer token if it exists.")
@coro
async def get(no_cache: bool) -> None:
    """Get a bearer token from OpenID Connect."""
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    try:
        token = await get_bearer_token(use_cache=not no_cache)
        logger.info("Bearer token: %s", token)
    except Exception:
        logger.exception("Error getting bearer token")


if __name__ == "__main__":
    cli()
