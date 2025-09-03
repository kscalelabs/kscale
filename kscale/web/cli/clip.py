"""Defines the CLI for managing clips."""

import logging

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.clip import ClipClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Manage clips."""
    pass


@cli.command()
@coro
async def list() -> None:
    """Lists all clips for the authenticated user."""
    client = ClipClient()
    clips = await client.get_clips()
    if clips:
        # Prepare table data
        table_data = [
            [
                click.style(clip.id, fg="blue"),
                clip.description or "N/A",
                clip.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "N/A" if clip.num_downloads is None else f"{clip.num_downloads:,}",
                "N/A" if clip.file_size is None else f"{clip.file_size:,} bytes",
            ]
            for clip in clips
        ]
        click.echo(
            tabulate(
                table_data,
                headers=["ID", "Description", "Created", "Downloads", "Size"],
                tablefmt="simple",
            )
        )
    else:
        click.echo(click.style("No clips found", fg="red"))


@cli.command()
@click.argument("clip_id")
@coro
async def get(clip_id: str) -> None:
    """Get information about a specific clip."""
    client = ClipClient()
    clip = await client.get_clip(clip_id)
    click.echo(f"ID: {click.style(clip.id, fg='blue')}")
    click.echo(f"Description: {click.style(clip.description or 'N/A', fg='green')}")
    click.echo(f"User ID: {click.style(clip.user_id, fg='yellow')}")
    click.echo(f"Created: {clip.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"Downloads: {clip.num_downloads or 0}")
    if clip.file_size:
        click.echo(f"File Size: {clip.file_size:,} bytes")


@cli.command()
@click.option("-d", "--description", type=str, default=None, help="Description for the clip")
@coro
async def create(description: str | None = None) -> None:
    """Create a new clip."""
    async with ClipClient() as client:
        clip = await client.create_clip(description)
    click.echo("Clip created:")
    click.echo(f"  ID: {click.style(clip.id, fg='blue')}")
    click.echo(f"  Description: {click.style(clip.description or 'N/A', fg='green')}")
    click.echo(f"  Created: {clip.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


@cli.command()
@click.argument("clip_id")
@click.option("-d", "--description", type=str, default=None, help="New description for the clip")
@coro
async def update(clip_id: str, description: str | None = None) -> None:
    """Update a clip's metadata."""
    async with ClipClient() as client:
        clip = await client.update_clip(clip_id, description)
    click.echo("Clip updated:")
    click.echo(f"  ID: {click.style(clip.id, fg='blue')}")
    click.echo(f"  Description: {click.style(clip.description or 'N/A', fg='green')}")


@cli.command()
@click.argument("clip_id")
@click.confirmation_option(prompt="Are you sure you want to delete this clip?")
@coro
async def delete(clip_id: str) -> None:
    """Delete a clip."""
    async with ClipClient() as client:
        await client.delete_clip(clip_id)
    click.echo(f"Clip deleted: {click.style(clip_id, fg='red')}")


@cli.command()
@click.argument("clip_id")
@click.argument("file_path", type=click.Path(exists=True))
@coro
async def upload(clip_id: str, file_path: str) -> None:
    """Upload a file for a clip."""
    async with ClipClient() as client:
        response = await client.upload_clip(clip_id, file_path)
    click.echo("File uploaded:")
    click.echo(f"  Filename: {click.style(response.filename, fg='green')}")
    click.echo(f"  Content Type: {response.content_type}")


@cli.command()
@click.argument("clip_id")
@click.option("-o", "--output", type=click.Path(), help="Output file path")
@coro
async def download(clip_id: str, output: str | None = None) -> None:
    """Download a clip file."""
    async with ClipClient() as client:
        if output:
            output_path = await client.download_clip_to_file(clip_id, output)
            click.echo(f"Clip downloaded to: {click.style(str(output_path), fg='green')}")
        else:
            download_response = await client.download_clip(clip_id)
            click.echo(f"Download URL: {click.style(download_response.url, fg='blue')}")
            click.echo(f"MD5 Hash: {download_response.md5_hash}")


if __name__ == "__main__":
    cli()
