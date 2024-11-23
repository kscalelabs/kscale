"""Utility functions for managing K-Recs in K-Scale WWW."""

import asyncio
import json
import logging
from pathlib import Path

import aiofiles
import click
import httpx
import krec

from kscale.utils.cli import coro
from kscale.web.gen.api import UploadKRecRequest
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_key, get_artifact_dir
from kscale.web.www_client import KScaleWWWClient

logger = logging.getLogger(__name__)


async def upload_krec(
    robot_id: str,
    file_path: Path,
    description: str | None = None,
    upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT,
) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = file_path.stat().st_size
    logger.info("Uploading K-Rec: %s", file_path)
    logger.info("File name: %s", file_path.name)
    logger.info("File size: %.1f MB", file_size / 1024 / 1024)

    if not file_path.suffix.lower() == ".krec":
        logger.warning("File extension is not .krec - are you sure this is a valid K-Rec file?")

    try:
        krec.KRec.load(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load K-Rec from {file_path} - are you sure this is a valid K-Rec file?") from e

    async with KScaleWWWClient(upload_timeout=upload_timeout) as client:
        create_response = await client.create_krec(
            UploadKRecRequest(
                robot_id=robot_id,
                name=file_path.name,
                description=description,
            )
        )

        logger.info("Initialized K-Rec upload with ID: %s", create_response["krec_id"])
        logger.info("Starting upload...")
        async with httpx.AsyncClient() as http_client:
            logger.info("Reading file content into memory...")
            async with aiofiles.open(file_path, "rb") as f:
                contents = await f.read()

            logger.info("Uploading file content to %s", create_response["upload_url"])
            response = await http_client.put(
                create_response["upload_url"],
                content=contents,
                headers={"Content-Type": "video/x-matroska"},
                timeout=upload_timeout,
            )
            response.raise_for_status()

        logger.info("Successfully uploaded K-Rec: %s", create_response["krec_id"])
        return create_response["krec_id"]


def upload_krec_sync(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    return asyncio.run(upload_krec(robot_id, file_path, name, description))


async def fetch_krec_info(krec_id: str, cache_dir: Path) -> dict:
    """Fetch K-Rec info from the server or cache."""
    response_path = cache_dir / "response.json"
    if response_path.exists():
        return json.loads(response_path.read_text())

    async with KScaleWWWClient() as client:
        try:
            response = await client.get_krec_info(krec_id)

            if not response:
                raise ValueError(f"Empty response from server for K-Rec ID: {krec_id}")

            response_path.write_text(json.dumps(response))
            return response
        except Exception as e:
            logger.error("Error fetching K-Rec info: %s", str(e))
            raise


async def download_krec(krec_id: str) -> Path:
    """Download a K-Rec file."""
    cache_dir = get_artifact_dir(krec_id)

    try:
        krec_info = await fetch_krec_info(krec_id, cache_dir)

        if not isinstance(krec_info, dict):
            logger.error("Unexpected response type: %s", type(krec_info))
            raise ValueError(f"Invalid response format for K-Rec ID: {krec_id}")

        if "url" not in krec_info or "filename" not in krec_info:
            logger.error("Response missing required fields: %s", krec_info)
            raise ValueError(f"Invalid response format for K-Rec ID: {krec_id}")

        download_url = krec_info["url"]
        filename = krec_info["filename"]
        full_path = cache_dir / filename

        if full_path.exists():
            logger.info("K-Rec already cached at %s", full_path)
            return full_path

        logger.info("Downloading K-Rec %s to %s", krec_id, full_path)

        api_key = get_api_key()
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/octet-stream"}

        async with httpx.AsyncClient() as client:
            async with client.stream("GET", download_url, headers=headers) as response:
                response.raise_for_status()

                with open(full_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

        logger.info("Successfully downloaded K-Rec to %s", full_path)
        return full_path

    except httpx.RequestError as e:
        logger.exception("Failed to fetch K-Rec: %s", str(e))
        raise
    except Exception as e:
        logger.exception("Unexpected error: %s", str(e))
        raise


def download_krec_sync(krec_id: str) -> Path:
    """Sync wrapper for download_krec."""
    return asyncio.run(download_krec(krec_id))


@click.group(name="krec")
def cli() -> None:
    """K-Scale K-Rec management commands."""
    pass


@cli.command()
@click.argument("robot_id")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--description", "-d", help="Description of the K-Rec")
@coro
async def upload(robot_id: str, file_path: Path, description: str | None = None) -> None:
    """Upload a K-Rec file."""
    krec_id = await upload_krec(robot_id, file_path, description)
    click.echo(f"Successfully uploaded K-Rec: {krec_id}")


@cli.command()
@click.argument("krec_id")
@coro
async def download(krec_id: str) -> None:
    """Download a K-Rec file."""
    file_path = await download_krec(krec_id)
    click.echo(f"Successfully downloaded K-Rec to: {file_path}")


if __name__ == "__main__":
    cli()
