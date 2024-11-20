"""Utility functions for managing K-Clips in the K-Scale store."""

import asyncio
import logging
from pathlib import Path

import click

from kscale.utils.cli import coro
from kscale.web.client import KScaleStoreClient
from kscale.web.gen.api import KClipPartCompleted, UploadKClipRequest

logger = logging.getLogger(__name__)

# Size of chunks for multipart upload (default 5MB)
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024


async def upload_kclip(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    file_size = file_path.stat().st_size

    async with KScaleStoreClient() as client:
        # Step 1: Initialize the upload
        create_response = await client.create_kclip(
            UploadKClipRequest(
                robot_id=robot_id, name=name, description=description, file_size=file_size, part_size=DEFAULT_CHUNK_SIZE
            )
        )

        logger.info(f"Initialized K-Clip upload with ID: {create_response.kclip_id}")

        # Step 2: Upload parts
        completed_parts: list[KClipPartCompleted] = []
        with open(file_path, "rb") as f:
            for part_number, url_info in enumerate(create_response.upload_details.presigned_urls, 1):
                chunk = f.read(create_response.upload_details.part_size)
                if not chunk:
                    break

                logger.info(f"Uploading part {part_number}/{len(create_response.upload_details.presigned_urls)}")

                # Upload the chunk using the presigned URL
                async with client.client as http_client:
                    # Convert the URL info dict to a string
                    presigned_url = str(url_info.get("url", ""))
                    response = await http_client.put(
                        presigned_url, content=chunk, headers={"Content-Type": "application/octet-stream"}
                    )
                    response.raise_for_status()

                    completed_parts.append(
                        KClipPartCompleted(part_number=part_number, etag=response.headers["ETag"].strip('"'))
                    )

        # Step 3: Complete the upload
        await client.complete_kclip_upload(
            kclip_id=create_response.kclip_id, upload_id=create_response.upload_details.upload_id, parts=completed_parts
        )

        logger.info(f"Successfully uploaded K-Clip: {create_response.kclip_id}")
        return create_response.kclip_id


def upload_kclip_sync(robot_id: str, file_path: Path, name: str, description: str | None = None) -> str:
    return asyncio.run(upload_kclip(robot_id, file_path, name, description))


@click.group()
def cli() -> None:
    """K-Scale K-Clip CLI tool."""
    pass


@cli.command()
@click.argument("robot_id")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--name", "-n", help="Name of the K-Clip", required=True)
@click.option("--description", "-d", help="Description of the K-Clip")
@coro
async def upload(robot_id: str, file_path: Path, name: str, description: str | None = None) -> None:
    """Upload a K-Clip file."""
    kclip_id = await upload_kclip(robot_id, file_path, name, description)
    click.echo(f"Successfully uploaded K-Clip: {kclip_id}")


if __name__ == "__main__":
    cli()
