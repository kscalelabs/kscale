"""Utility functions for managing artifacts in K-Scale WWW."""

import logging
import shutil
import tarfile
from pathlib import Path

import click
import httpx
import requests

from kscale.utils.cli import coro
from kscale.web.gen.api import SingleArtifactResponse, UploadArtifactResponse
from kscale.web.utils import get_api_key, get_artifact_dir, get_cache_dir
from kscale.web.www_client import KScaleWWWClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {
    ".urdf",
    ".mjcf",
    ".stl",
    ".obj",
    ".dae",
    ".png",
    ".jpg",
    ".jpeg",
}


async def fetch_urdf_info(artifact_id: str, cache_dir: Path) -> SingleArtifactResponse:
    response_path = cache_dir / "response.json"
    if response_path.exists():
        return SingleArtifactResponse.model_validate_json(response_path.read_text())
    async with KScaleWWWClient() as client:
        response = await client.get_artifact_info(artifact_id)
    response_path.write_text(response.model_dump_json())
    return response


async def download_artifact(artifact_url: str, cache_dir: Path) -> Path:
    filename = cache_dir / Path(artifact_url).name
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
    }

    if not filename.exists():
        logger.info("Downloading artifact from %s", artifact_url)

        async with httpx.AsyncClient() as client:
            response = await client.get(artifact_url, headers=headers)
            response.raise_for_status()
            filename.write_bytes(response.content)
            logger.info("Artifact downloaded to %s", filename)
    else:
        logger.info("Artifact already cached at %s", filename)

    # Extract the .tgz file
    extract_dir = cache_dir / filename.stem
    if not extract_dir.exists():
        logger.info("Extracting %s to %s", filename, extract_dir)
        with tarfile.open(filename, "r:gz") as tar:
            tar.extractall(path=extract_dir)
    else:
        logger.info("Artifact already extracted at %s", extract_dir)

    return extract_dir


def create_tarball(folder_path: Path, output_filename: str, cache_dir: Path) -> Path:
    tarball_path = cache_dir / output_filename
    with tarfile.open(tarball_path, "w:gz") as tar:
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_SUFFIXES:
                tar.add(file_path, arcname=file_path.relative_to(folder_path))
                logger.info("Added %s to tarball", file_path)
            else:
                logger.warning("Skipping %s", file_path)
    logger.info("Created tarball %s", tarball_path)
    return tarball_path


async def download_urdf(artifact_id: str) -> Path:
    cache_dir = get_artifact_dir(artifact_id)
    try:
        urdf_info = await fetch_urdf_info(artifact_id, cache_dir)
        artifact_url = urdf_info.urls.large
        return await download_artifact(artifact_url, cache_dir)

    except requests.RequestException:
        logger.exception("Failed to fetch URDF info")
        raise


async def show_urdf_info(artifact_id: str) -> None:
    try:
        urdf_info = await fetch_urdf_info(artifact_id, get_artifact_dir(artifact_id))
        logger.info("URDF Artifact ID: %s", urdf_info.artifact_id)
        logger.info("URDF URL: %s", urdf_info.urls.large)
    except requests.RequestException:
        logger.exception("Failed to fetch URDF info")
        raise


async def remove_local_urdf(artifact_id: str) -> None:
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


async def upload_urdf(listing_id: str, root_dir: Path) -> UploadArtifactResponse:
    tarball_path = create_tarball(root_dir, "robot.tgz", get_artifact_dir(listing_id))

    async with KScaleWWWClient() as client:
        response = await client.upload_artifact(listing_id, str(tarball_path))

    logger.info("Uploaded artifacts: %s", [artifact.artifact_id for artifact in response.artifacts])
    return response


async def upload_urdf_cli(listing_id: str, root_dir: Path) -> UploadArtifactResponse:
    response = await upload_urdf(listing_id, root_dir)
    return response


@click.group()
def cli() -> None:
    """K-Scale URDF Store CLI tool."""
    pass


@cli.command()
@click.argument("artifact_id")
@coro
async def download(artifact_id: str) -> None:
    """Download a URDF artifact."""
    await download_urdf(artifact_id)


@cli.command()
@click.argument("artifact_id")
@coro
async def info(artifact_id: str) -> None:
    """Show information about a URDF artifact."""
    await show_urdf_info(artifact_id)


@cli.command("remove-local")
@click.argument("artifact_id")
@coro
async def remove_local(artifact_id: str) -> None:
    """Remove local cache of a URDF artifact."""
    await remove_local_urdf(artifact_id)


@cli.command()
@click.argument("listing_id")
@click.argument("root_dir", type=click.Path(exists=True, path_type=Path))
@coro
async def upload(listing_id: str, root_dir: Path) -> None:
    """Upload a URDF artifact."""
    await upload_urdf_cli(listing_id, root_dir)


if __name__ == "__main__":
    # python -m kscale.web.urdf
    cli()
