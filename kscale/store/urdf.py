"""Utility functions for managing artifacts in the K-Scale store."""

import argparse
import asyncio
import logging
import os
import sys
import tarfile
from pathlib import Path
from typing import Literal, Sequence

import httpx
import requests

from kscale.conf import Settings
from kscale.store.gen.api import UrdfResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_api_key() -> str:
    api_key = Settings.load().store.api_key
    if not api_key:
        raise ValueError(
            "API key not found! Get one here and set it as the `KSCALE_API_KEY` environment variable or in your"
            "config file: https://kscale.store/keys"
        )
    return api_key


def get_cache_dir() -> Path:
    return Path(Settings.load().store.cache_dir).expanduser().resolve()


def fetch_urdf_info(listing_id: str) -> UrdfResponse:
    url = f"https://api.kscale.store/urdf/info/{listing_id}"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return UrdfResponse(**response.json())


async def download_artifact(artifact_url: str, cache_dir: Path) -> str:
    filename = os.path.join(cache_dir, artifact_url.split("/")[-1])
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
    }

    if not os.path.exists(filename):
        logger.info("Downloading artifact from %s" % artifact_url)

        async with httpx.AsyncClient() as client:
            response = await client.get(artifact_url, headers=headers)
            response.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
            logger.info("Artifact downloaded to %s" % filename)
    else:
        logger.info("Artifact already cached at %s" % filename)

    # Extract the .tgz file
    extract_dir = os.path.join(cache_dir, os.path.splitext(os.path.basename(filename))[0])
    if not os.path.exists(extract_dir):
        logger.info(f"Extracting {filename} to {extract_dir}")
        with tarfile.open(filename, "r:gz") as tar:
            tar.extractall(path=extract_dir)
        logger.info("Extraction complete")
    else:
        logger.info("Artifact already extracted at %s" % extract_dir)

    return extract_dir


def create_tarball(folder_path: str | Path, output_filename: str, cache_dir: Path) -> str:
    tarball_path = os.path.join(cache_dir, output_filename)
    with tarfile.open(tarball_path, "w:gz") as tar:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                tar.add(file_path, arcname=arcname)
                logger.info("Added %s as %s" % (file_path, arcname))
    logger.info("Created tarball %s" % tarball_path)
    return tarball_path


async def upload_artifact(tarball_path: str, listing_id: str) -> None:
    url = f"https://api.kscale.store/urdf/upload/{listing_id}"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
    }

    async with httpx.AsyncClient() as client:
        with open(tarball_path, "rb") as f:
            files = {"file": (f.name, f, "application/gzip")}
            response = await client.post(url, headers=headers, files=files)

            response.raise_for_status()

    logger.info("Uploaded artifact to %s" % url)


def main(args: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="K-Scale URDF Store", add_help=False)
    parser.add_argument(
        "command",
        choices=["get", "info", "upload"],
        help="The command to run",
    )
    parser.add_argument("listing_id", help="The listing ID to operate on")
    parsed_args, remaining_args = parser.parse_known_args(args)

    command: Literal["get", "info", "upload"] = parsed_args.command
    listing_id: str = parsed_args.listing_id

    def get_listing_dir() -> Path:
        (cache_dir := get_cache_dir() / listing_id).mkdir(parents=True, exist_ok=True)
        return cache_dir

    match command:
        case "get":
            try:
                urdf_info = fetch_urdf_info(listing_id)

                if urdf_info.urdf:
                    artifact_url = urdf_info.urdf.url
                    asyncio.run(download_artifact(artifact_url, get_listing_dir()))
                else:
                    logger.info("No URDF found for listing %s" % listing_id)
            except requests.RequestException as e:
                logger.error("Failed to fetch URDF info: %s" % e)
                sys.exit(1)

        case "info":
            try:
                urdf_info = fetch_urdf_info(listing_id)

                if urdf_info.urdf:
                    logger.info("URDF Artifact ID: %s" % urdf_info.urdf.artifact_id)
                    logger.info("URDF URL: %s" % urdf_info.urdf.url)
                else:
                    logger.info("No URDF found for listing %s" % listing_id)
            except requests.RequestException as e:
                logger.error("Failed to fetch URDF info: %s" % e)
                sys.exit(1)

        case "upload":
            parser = argparse.ArgumentParser(description="Upload a URDF artifact to the K-Scale store")
            parser.add_argument("folder_path", help="The path to the folder containing the URDF files")
            parsed_args = parser.parse_args(remaining_args)
            folder_path = Path(parsed_args.folder_path).expanduser().resolve()

            output_filename = f"{listing_id}.tgz"
            tarball_path = create_tarball(folder_path, output_filename, get_listing_dir())

            try:
                urdf_info = fetch_urdf_info(listing_id)
                asyncio.run(upload_artifact(tarball_path, listing_id))
            except requests.RequestException as e:
                logger.error("Failed to upload artifact: %s" % e)
                sys.exit(1)

        case _:
            logger.error("Invalid command")
            sys.exit(1)


if __name__ == "__main__":
    main()
