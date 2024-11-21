"""Utility functions for managing K-Recs in the K-Scale store."""

import asyncio
import logging
from pathlib import Path

import click

from kscale.utils.cli import coro
from kscale.web.gen.api import KRecPartCompleted, UploadKRecRequest
from kscale.web.www_client import KScaleStoreClient

logger = logging.getLogger(__name__)

# Size of chunks for multipart upload (default 5MB)
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024


async def upload_krec(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    file_size = file_path.stat().st_size

    async with KScaleStoreClient() as client:
        # Step 1: Initialize the upload
        create_response = await client.create_krec(
            UploadKRecRequest(
                robot_id=robot_id, name=name, description=description, file_size=file_size, part_size=DEFAULT_CHUNK_SIZE
            )
        )

        logger.info("Initialized K-Rec upload with ID: %s", create_response.krec_id)

        # Step 2: Upload parts
        completed_parts: list[KRecPartCompleted] = []
        with open(file_path, "rb") as f:
            for part_number, url_info in enumerate(create_response.upload_details.presigned_urls, 1):
                chunk = f.read(create_response.upload_details.part_size)
                if not chunk:
                    break

                logger.info("Uploading part %d/%d", part_number, len(create_response.upload_details.presigned_urls))

                # Upload the chunk using the presigned URL
                presigned_url = str(url_info.get("url", ""))
                try:
                    response = await client.client.put(
                        presigned_url, content=chunk, headers={"Content-Type": "application/octet-stream"}
                    )
                    response.raise_for_status()

                    etag = response.headers.get("ETag")
                    if not etag:
                        raise ValueError("No ETag in response headers for part %d", part_number)

                    completed_parts.append(KRecPartCompleted(part_number=part_number, etag=etag.strip('"')))
                    logger.info("Successfully uploaded part %d with ETag: %s", part_number, etag)
                except Exception as e:
                    logger.error("Failed to upload part %d: %s", part_number, str(e))
                    raise

        # Step 3: Complete the upload
        logger.info("Attempting to complete upload with %d parts", len(completed_parts))
        try:
            completion_response = await client.complete_krec_upload(
                krec_id=create_response.krec_id,
                upload_id=create_response.upload_details.upload_id,
                parts=completed_parts,
            )
            logger.info("Complete upload response: %s", completion_response)
        except Exception as e:
            logger.error("Failed to complete upload: %s", str(e))
            raise

        logger.info("Successfully uploaded K-Rec: %s", create_response.krec_id)
        return create_response.krec_id


def upload_krec_sync(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    return asyncio.run(upload_krec(robot_id, file_path, name, description))


@click.group()
def cli() -> None:
    """K-Scale K-Rec CLI tool."""
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


if __name__ == "__main__":
    cli()
