"""Utility functions for managing artifacts in the K-Scale store."""

import asyncio
import logging
import os
import sys
import tarfile
from typing import Sequence

import httpx
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_DIR = os.path.expanduser("~/.cache/kscale")


def fetch_urdf_info(listing_id: str) -> dict:
    url = f"https://api.kscale.store/urdf/info/{listing_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def download_artifact(artifact_url: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    filename = os.path.join(cache_dir, artifact_url.split("/")[-1])

    if not os.path.exists(filename):
        logger.info(f"Downloading artifact from {artifact_url}")
        response = requests.get(artifact_url, stream=True)
        response.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Artifact downloaded to {filename}")
    else:
        logger.info(f"Artifact already cached at {filename}")

    # Extract the .tgz file
    extract_dir = os.path.join(cache_dir, os.path.splitext(os.path.basename(filename))[0])
    if not os.path.exists(extract_dir):
        logger.info(f"Extracting {filename} to {extract_dir}")
        with tarfile.open(filename, "r:gz") as tar:
            tar.extractall(path=extract_dir)
        logger.info("Extraction complete")
    else:
        logger.info(f"Artifact already extracted at {extract_dir}")

    return extract_dir


def create_tarball(folder_path: str, output_filename: str) -> str:
    tarball_path = os.path.join(CACHE_DIR, output_filename)
    with tarfile.open(tarball_path, "w:gz") as tar:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                tar.add(file_path, arcname=arcname)
                logger.info(f"Added {file_path} as {arcname}")
    logger.info(f"Created tarball {tarball_path}")
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

    logger.info(f"Uploaded artifact to {url}")


def main(args: Sequence[str] | None = None) -> None:

    command = args[0]
    listing_id = args[1]

    if command == "info":
        try:
            urdf_info = fetch_urdf_info(listing_id)
            artifact_url = urdf_info["urdf"]["url"]
            download_artifact(artifact_url, CACHE_DIR)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch URDF info: {e}")
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
            logger.error(f"Failed to upload artifact: {e}")
            sys.exit(1)
    else:
        print("Invalid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
