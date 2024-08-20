"""Utility functions for managing artifacts in the K-Scale store."""

import asyncio
import logging
import os
import sys
import tarfile
from typing import Sequence

import httpx
import requests

from kscale.store.gen.api import UrdfResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_DIR = os.path.expanduser("~/.cache/kscale")


def fetch_urdf_info(listing_id: str, api_key: str = "") -> UrdfResponse:
    url = f"https://api.kscale.store/urdf/info/{listing_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return UrdfResponse(**response.json())


async def download_artifact(artifact_url: str, cache_dir: str, api_key: str = None) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    filename = os.path.join(cache_dir, artifact_url.split("/")[-1])
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    if not os.path.exists(filename):
        logger.info("Downloading artifact from %s" % artifact_url)

        async with httpx.AsyncClient() as client:
            response = await client.get(artifact_url, headers=headers)
            response.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
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


def create_tarball(folder_path: str, output_filename: str) -> str:
    tarball_path = os.path.join(CACHE_DIR, output_filename)
    with tarfile.open(tarball_path, "w:gz") as tar:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                tar.add(file_path, arcname=arcname)
                logger.info("Added %s as %s" % (file_path, arcname))
    logger.info("Created tarball %s" % tarball_path)
    return tarball_path


async def upload_artifact(tarball_path: str, listing_id: str, api_key: str) -> None:
    url = f"https://api.kscale.store/urdf/upload/{listing_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient() as client:
        with open(tarball_path, "rb") as f:
            files = {"file": (f.name, f, "application/gzip")}
            response = await client.post(url, headers=headers, files=files)

            response.raise_for_status()

    logger.info("Uploaded artifact to %s" % url)


def main(args: Sequence[str] | None = None) -> None:

    command = args[0]
    listing_id = args[1]

    if command == "get":
        try:
            api_key = os.getenv("KSCALE_API_KEY") or (args[2] if len(args) >= 3 else None)
            urdf_info = fetch_urdf_info(listing_id, api_key)
            
            if urdf_info.urdf:
                artifact_url = urdf_info.urdf.url
                asyncio.run(download_artifact(artifact_url, CACHE_DIR, api_key))
            else:
                logger.info("No URDF found for listing %s" % listing_id)
        except requests.RequestException as e:
            logger.error("Failed to fetch URDF info: %s" % e)
            sys.exit(1)
    elif command == "info":
        try:
            api_key = os.getenv("KSCALE_API_KEY") or (args[2] if len(args) >= 3 else None)
            urdf_info = fetch_urdf_info(listing_id, api_key)

            if urdf_info.urdf:
                logger.info("URDF Artifact ID: %s" % urdf_info.urdf.artifact_id)
                logger.info("URDF URL: %s" % urdf_info.urdf.url)
            else:
                logger.info("No URDF found for listing %s" % listing_id)
        except requests.RequestException as e:
            logger.error("Failed to fetch URDF info: %s" % e)
            sys.exit(1)
    elif command == "upload":
        folder_path = args[2]
        api_key = os.getenv("KSCALE_API_KEY") or args[3]  # Use the environment variable if available

        output_filename = f"{listing_id}.tgz"
        tarball_path = create_tarball(folder_path, output_filename)

        try:
            urdf_info = fetch_urdf_info(listing_id)
            asyncio.run(upload_artifact(tarball_path, listing_id, api_key))
        except requests.RequestException as e:
            logger.error("Failed to upload artifact: %s" % e)
            sys.exit(1)
    else:
        logger.error("Invalid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
