"""Utility functions for managing artifacts in the K-Scale store."""

import argparse
import asyncio
import logging
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Literal, Sequence, get_args

import httpx
import requests

from kscale.conf import Settings
from kscale.store.client import KScaleStoreClient
from kscale.store.gen.api import SingleArtifactResponse, UploadArtifactResponse
from kscale.store.utils import get_api_key

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


def get_cache_dir() -> Path:
    return Path(Settings.load().store.cache_dir).expanduser().resolve()


def get_artifact_dir(artifact_id: str) -> Path:
    cache_dir = get_cache_dir() / artifact_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


async def fetch_urdf_info(artifact_id: str, cache_dir: Path) -> SingleArtifactResponse:
    response_path = cache_dir / "response.json"
    if response_path.exists():
        return SingleArtifactResponse.model_validate_json(response_path.read_text())
    async with KScaleStoreClient() as client:
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

    async with KScaleStoreClient() as client:
        response = await client.upload_artifact(listing_id, str(tarball_path))

    logger.info("Uploaded artifacts: %s", [artifact.artifact_id for artifact in response.artifacts])
    return response


async def upload_urdf_cli(listing_id: str, args: Sequence[str]) -> UploadArtifactResponse:
    parser = argparse.ArgumentParser(description="K-Scale URDF Store", add_help=False)
    parser.add_argument("root_dir", type=Path, help="The path to the root directory to upload")
    parsed_args = parser.parse_args(args)

    root_dir = parsed_args.root_dir
    response = await upload_urdf(listing_id, root_dir)
    return response


Command = Literal["download", "info", "upload", "remove-local"]


async def main(args: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="K-Scale URDF Store", add_help=False)
    parser.add_argument("command", choices=get_args(Command), help="The command to run")
    parser.add_argument("id", help="The ID to use (artifact when downloading, listing when uploading)")
    parsed_args, remaining_args = parser.parse_known_args(args)

    command: Command = parsed_args.command
    id: str = parsed_args.id

    match command:
        case "download":
            await download_urdf(id)

        case "info":
            await show_urdf_info(id)

        case "remove-local":
            await remove_local_urdf(id)

        case "upload":
            await upload_urdf_cli(id, remaining_args)

        case _:
            logger.error("Invalid command")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
