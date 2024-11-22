"""Utility functions for managing K-Recs in the K-Scale store."""

import asyncio
import base64
import hashlib
import json
import logging
from pathlib import Path
import os
import sys

import click
import httpx

from kscale.utils.checksum import FileChecksum
from kscale.utils.cli import coro
from kscale.web.gen.api import KRecPartCompleted, UploadKRecRequest
from kscale.web.utils import get_api_key, get_artifact_dir
from kscale.web.www_client import KScaleStoreClient

logger = logging.getLogger(__name__)

# Size of chunks for multipart upload (default 5MB)
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024


async def upload_krec(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    # Add environment logging at the start
    logger.debug("Environment configuration:")
    logger.debug("KSCALE_API_ROOT: %s", os.getenv('KSCALE_API_ROOT'))
    logger.debug("Python version: %s", sys.version)
    logger.debug("HTTPX version: %s", httpx.__version__)

    # Calculate checksum and file size before upload
    checksum, file_size = await FileChecksum.calculate(str(file_path))
    logger.info("Uploading K-Rec: %s", file_path)
    logger.info("File name: %s", file_path.name)
    logger.info("File size: %.1f MB", file_size / 1024 / 1024)

    async with KScaleStoreClient() as client:
        # Step 1: Initialize the upload
        create_response = await client.create_krec(
            UploadKRecRequest(
                robot_id=robot_id,
                name=name,
                description=description,
                file_size=file_size,
                part_size=DEFAULT_CHUNK_SIZE,
            )
        )

        logger.info("Initialized K-Rec upload with ID: %s", create_response.krec_id)

        # Step 2: Upload parts
        completed_parts: list[KRecPartCompleted] = []
        with open(file_path, "rb") as f:
            for presigned_url_info in create_response.upload_details.presigned_urls:
                presigned_url = str(presigned_url_info["url"])
                part_number = int(presigned_url_info["part_number"])

                chunk = f.read(create_response.upload_details.part_size)
                if not chunk:
                    break

                logger.info("Uploading part %d/%d", part_number, len(create_response.upload_details.presigned_urls))

                chunk_checksum_bytes = hashlib.sha256(chunk).digest()
                chunk_checksum_b64 = base64.b64encode(chunk_checksum_bytes).decode()

                try:
                    logger.debug("Uploading part %d with:", part_number)
                    logger.debug("URL: %s", presigned_url)
                    logger.debug("Chunk size: %d bytes", len(chunk))
                    logger.debug("Headers: %s", {
                        "Content-Length": str(len(chunk)),
                        "Content-Type": "application/octet-stream",
                        "x-amz-checksum-sha256": chunk_checksum_b64,
                    })

                    response = await client.client.put(
                        presigned_url,
                        content=chunk,
                        headers={
                            "Content-Length": str(len(chunk)),
                            "Content-Type": "application/octet-stream",
                            "x-amz-checksum-sha256": chunk_checksum_b64,
                        },
                    )
                    response.raise_for_status()

                    etag = response.headers.get("ETag")
                    if not etag:
                        raise ValueError(f"No ETag in response headers for part {part_number}")

                    completed_parts.append(
                        KRecPartCompleted(part_number=part_number, etag=etag.strip('"'), checksum=chunk_checksum_b64)
                    )
                    logger.info("Successfully uploaded part %d with ETag: %s", part_number, etag)

                    # Log response details
                    logger.debug("Response status: %d", response.status_code)
                    logger.debug("Response headers: %s", dict(response.headers))
                    if response.status_code != 200:
                        logger.debug("Response body: %s", response.text)
                except Exception as e:
                    logger.error("Failed to upload part %d: %s", part_number, str(e))
                    raise

        # Step 3: Complete the upload
        logger.info("Attempting to complete upload with %d parts", len(completed_parts))
        try:
            await client.complete_krec_upload(
                krec_id=create_response.krec_id,
                upload_id=create_response.upload_details.upload_id,
                parts=completed_parts,
            )
            logger.info("Upload completed successfully")
        except Exception as e:
            logger.error("Failed to complete upload: %s", str(e))
            raise

        logger.info("Successfully uploaded K-Rec: %s", create_response.krec_id)
        return create_response.krec_id


def upload_krec_sync(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    return asyncio.run(upload_krec(robot_id, file_path, name, description))


async def fetch_krec_info(krec_id: str, cache_dir: Path) -> dict:
    """Fetch K-Rec info from the server or cache."""
    response_path = cache_dir / "response.json"
    if response_path.exists():
        return json.loads(response_path.read_text())

    async with KScaleStoreClient() as client:
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
        expected_checksum = krec_info.get("checksum")

        full_path = cache_dir / filename

        if full_path.exists():
            if expected_checksum:
                actual_checksum, _ = await FileChecksum.calculate(str(full_path))
                if actual_checksum == expected_checksum:
                    logger.info("K-Rec already cached at %s (checksum verified)", full_path)
                    return full_path
                else:
                    logger.warning("Cached file checksum mismatch, re-downloading")
            else:
                logger.info("K-Rec already cached at %s (no checksum to verify)", full_path)
                return full_path

        logger.info("Downloading K-Rec %s to %s", krec_id, full_path)

        api_key = get_api_key()
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/octet-stream"}

        sha256_hash = hashlib.sha256()

        async with httpx.AsyncClient() as client:
            async with client.stream("GET", download_url, headers=headers) as response:
                response.raise_for_status()

                with open(full_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        FileChecksum.update_hash(sha256_hash, chunk)
                        f.write(chunk)

        actual_checksum = sha256_hash.hexdigest()

        if expected_checksum and actual_checksum != expected_checksum:
            logger.error("Checksum mismatch! Expected: %s, Got: %s", expected_checksum, actual_checksum)
            full_path.unlink()
            raise ValueError("Downloaded file checksum verification failed")

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
@click.option("--name", "-n", help="Name of the K-Rec", required=True)
@click.option("--description", "-d", help="Description of the K-Rec")
@coro
async def upload(robot_id: str, file_path: Path, name: str, description: str | None = None) -> None:
    """Upload a K-Rec file."""
    krec_id = await upload_krec(robot_id, file_path, name, description)
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
