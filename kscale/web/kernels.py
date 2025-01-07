"""Utility functions for managing kernel images in K-Scale WWW."""

import hashlib
import logging
import shutil
from pathlib import Path

import aiofiles
import click
import httpx

from kscale.utils.checksum import FileChecksum
from kscale.utils.cli import coro
from kscale.web.gen.api import SingleArtifactResponse
from kscale.web.token import get_bearer_token
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_artifact_dir, get_cache_dir
from kscale.web.www_client import KScaleWWWClient

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".img"}


async def fetch_kernel_image_info(artifact_id: str, cache_dir: Path) -> SingleArtifactResponse:
    response_path = cache_dir / "response.json"
    if response_path.exists():
        return SingleArtifactResponse.model_validate_json(response_path.read_text())
    async with KScaleWWWClient() as client:
        response = await client.get_artifact_info(artifact_id)
    response_path.write_text(response.model_dump_json())
    return response


async def download_kernel_image(artifact_id: str) -> Path:
    """Download a kernel image artifact."""
    cache_dir = get_artifact_dir(artifact_id)
    try:
        kernel_image_info = await fetch_kernel_image_info(artifact_id, cache_dir)
        artifact_url = kernel_image_info.urls.large

        original_name = Path(artifact_url).name
        if not original_name.endswith(".img"):
            filename = cache_dir / f"{original_name}.img"
        else:
            filename = cache_dir / original_name

        headers = {
            "Authorization": f"Bearer {await get_bearer_token()}",
            "Accept": "application/octet-stream",
        }

        if not filename.exists():
            logger.info("Downloading kernel image...")
            sha256_hash = hashlib.sha256()

            async with httpx.AsyncClient() as client:
                async with client.stream("GET", artifact_url, headers=headers) as response:
                    response.raise_for_status()

                    async with aiofiles.open(filename, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            FileChecksum.update_hash(sha256_hash, chunk)
                            await f.write(chunk)

            logger.info("Kernel image downloaded to %s", filename)
        else:
            logger.info("Kernel image already cached at %s", filename)

        return filename

    except httpx.RequestError:
        logger.exception("Failed to fetch kernel image")
        raise


async def show_kernel_image_info(artifact_id: str) -> None:
    """Show information about a kernel image artifact."""
    try:
        kernel_image_info = await fetch_kernel_image_info(artifact_id, get_artifact_dir(artifact_id))
        logger.info("Kernel Image Artifact ID: %s", kernel_image_info.artifact_id)
        logger.info("Kernel Image URL: %s", kernel_image_info.urls.large)
    except httpx.RequestError:
        logger.exception("Failed to fetch kernel image info")
        raise


async def remove_local_kernel_image(artifact_id: str) -> None:
    """Remove local cache of a kernel image artifact."""
    try:
        if artifact_id.lower() == "all":
            cache_dir = get_cache_dir()
            if cache_dir.exists():
                logger.info("Removing all local caches at %s", cache_dir)
                shutil.rmtree(cache_dir)
            else:
                logger.error("No local caches found")
        else:
            artifact_dir = get_artifact_dir(artifact_id)
            if artifact_dir.exists():
                logger.info("Removing local cache at %s", artifact_dir)
                shutil.rmtree(artifact_dir)
            else:
                logger.error("No local cache found for artifact %s", artifact_id)

    except Exception:
        logger.error("Failed to remove local cache")
        raise


async def upload_kernel_image(
    listing_id: str,
    image_path: Path,
    upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT,
) -> SingleArtifactResponse:
    """Upload a kernel image."""
    if image_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Invalid file type. Must be one of: %s", ALLOWED_SUFFIXES)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    checksum, file_size = await FileChecksum.calculate(str(image_path))
    logger.info("Uploading kernel image: %s", image_path)
    logger.info("File name: %s", image_path.name)
    logger.info("File size: %.1f MB", file_size / 1024 / 1024)

    async with KScaleWWWClient(upload_timeout=upload_timeout) as client:
        presigned_data = await client.get_presigned_url(
            listing_id=listing_id,
            file_name=image_path.name,
            checksum=checksum,
        )

        logger.info("Starting upload...")
        async with httpx.AsyncClient() as http_client:
            logger.info("Reading file content into memory...")
            async with aiofiles.open(image_path, "rb") as f:
                contents = await f.read()

            logger.info("Uploading file content to %s", presigned_data["upload_url"])
            response = await http_client.put(
                presigned_data["upload_url"],
                content=contents,
                headers={"Content-Type": "application/x-raw-disk-image"},
                timeout=upload_timeout,
            )
            response.raise_for_status()

        artifact_response: SingleArtifactResponse = await client.get_artifact_info(presigned_data["artifact_id"])
        logger.info("Uploaded artifact: %s", artifact_response.artifact_id)
        return artifact_response


async def upload_kernel_image_cli(
    listing_id: str, image_path: Path, upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT
) -> SingleArtifactResponse:
    """CLI wrapper for upload_kernel_image."""
    response = await upload_kernel_image(listing_id, image_path, upload_timeout=upload_timeout)
    return response


@click.group()
def cli() -> None:
    """K-Scale Kernel Image CLI tool."""
    pass


@cli.command()
@click.argument("artifact_id")
@coro
async def download(artifact_id: str) -> None:
    """Download a kernel image artifact."""
    await download_kernel_image(artifact_id)


@cli.command()
@click.argument("artifact_id")
@coro
async def info(artifact_id: str) -> None:
    """Show information about a kernel image artifact."""
    await show_kernel_image_info(artifact_id)


@cli.command("remove-local")
@click.argument("artifact_id")
@coro
async def remove_local(artifact_id: str) -> None:
    """Remove local cache of a kernel image artifact."""
    await remove_local_kernel_image(artifact_id)


@cli.command()
@click.argument("listing_id")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--upload-timeout", type=float, default=DEFAULT_UPLOAD_TIMEOUT, help="Timeout in seconds for upload operations"
)
@coro
async def upload(listing_id: str, image_path: Path, upload_timeout: float) -> None:
    """Upload a kernel image artifact."""
    await upload_kernel_image_cli(listing_id, image_path, upload_timeout=upload_timeout)


if __name__ == "__main__":
    cli()
