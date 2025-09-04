"""Defines the CLI for managing groups."""

import logging

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.group import GroupClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Manage groups."""
    pass


@cli.command()
@coro
async def list() -> None:
    """Lists all groups for the authenticated user."""
    client = GroupClient()
    groups = await client.get_groups()
    if groups:
        # Prepare table data
        table_data = [
            [
                click.style(group.id, fg="blue"),
                click.style(group.name, fg="green"),
                group.description or "N/A",
                group.created_at,
                "Active" if group.is_active else "Inactive",
            ]
            for group in groups
        ]
        click.echo(
            tabulate(
                table_data,
                headers=["ID", "Name", "Description", "Created", "Status"],
                tablefmt="simple",
            )
        )
    else:
        click.echo(click.style("No groups found", fg="red"))


@cli.command()
@click.argument("group_id")
@coro
async def get(group_id: str) -> None:
    """Get information about a specific group."""
    client = GroupClient()
    group = await client.get_group(group_id)
    click.echo(f"ID: {click.style(group.id, fg='blue')}")
    click.echo(f"Name: {click.style(group.name, fg='green')}")
    click.echo(f"Description: {click.style(group.description or 'N/A', fg='yellow')}")
    click.echo(f"Owner ID: {click.style(group.owner_id, fg='cyan')}")
    click.echo(f"Created: {group.created_at}")
    click.echo(f"Updated: {group.updated_at}")
    click.echo(f"Status: {'Active' if group.is_active else 'Inactive'}")


@cli.command()
@click.argument("name")
@click.option("-d", "--description", type=str, default=None, help="Description for the group")
@coro
async def create(name: str, description: str | None = None) -> None:
    """Create a new group."""
    async with GroupClient() as client:
        group = await client.create_group(name, description)
    click.echo("Group created:")
    click.echo(f"  ID: {click.style(group.id, fg='blue')}")
    click.echo(f"  Name: {click.style(group.name, fg='green')}")
    click.echo(f"  Description: {click.style(group.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("group_id")
@click.option("-n", "--name", type=str, default=None, help="New name for the group")
@click.option("-d", "--description", type=str, default=None, help="New description for the group")
@coro
async def update(group_id: str, name: str | None = None, description: str | None = None) -> None:
    """Update a group's metadata."""
    async with GroupClient() as client:
        group = await client.update_group(group_id, name, description)
    click.echo("Group updated:")
    click.echo(f"  ID: {click.style(group.id, fg='blue')}")
    click.echo(f"  Name: {click.style(group.name, fg='green')}")
    click.echo(f"  Description: {click.style(group.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("group_id")
@click.confirmation_option(prompt="Are you sure you want to delete this group?")
@coro
async def delete(group_id: str) -> None:
    """Delete a group."""
    async with GroupClient() as client:
        await client.delete_group(group_id)
    click.echo(f"Group deleted: {click.style(group_id, fg='red')}")


@cli.group()
def membership() -> None:
    """Manage group memberships."""
    pass


@membership.command("list")
@click.argument("group_id")
@coro
async def list_memberships(group_id: str) -> None:
    """List all memberships for a group."""
    client = GroupClient()
    memberships = await client.get_group_memberships(group_id)
    if memberships:
        table_data = [
            [
                click.style(membership.id, fg="blue"),
                click.style(membership.user_id, fg="green"),
                membership.status,
                membership.requested_at,
                membership.approved_at or "N/A",
                membership.approved_by or "N/A",
            ]
            for membership in memberships
        ]
        click.echo(
            tabulate(
                table_data,
                headers=["ID", "User ID", "Status", "Requested", "Approved", "Approved By"],
                tablefmt="simple",
            )
        )
    else:
        click.echo(click.style("No memberships found", fg="red"))


@membership.command("request")
@click.argument("group_id")
@coro
async def request_membership(group_id: str) -> None:
    """Request to join a group."""
    async with GroupClient() as client:
        membership = await client.request_group_membership(group_id)
    click.echo("Membership request sent:")
    click.echo(f"  ID: {click.style(membership.id, fg='blue')}")
    click.echo(f"  Status: {membership.status}")


@membership.command("approve")
@click.argument("group_id")
@click.argument("user_id")
@coro
async def approve_membership(group_id: str, user_id: str) -> None:
    """Approve a membership request."""
    async with GroupClient() as client:
        membership = await client.approve_group_membership(group_id, user_id)
    click.echo("Membership approved:")
    click.echo(f"  ID: {click.style(membership.id, fg='blue')}")
    click.echo(f"  Status: {membership.status}")


@membership.command("reject")
@click.argument("group_id")
@click.argument("user_id")
@click.confirmation_option(prompt="Are you sure you want to reject this membership?")
@coro
async def reject_membership(group_id: str, user_id: str) -> None:
    """Reject a membership request."""
    async with GroupClient() as client:
        await client.reject_group_membership(group_id, user_id)
    click.echo(f"Membership rejected for user: {click.style(user_id, fg='red')}")


@cli.group()
def share() -> None:
    """Manage group resource sharing."""
    pass


@share.command("list")
@click.argument("group_id")
@coro
async def list_shares(group_id: str) -> None:
    """List all resources shared with a group."""
    client = GroupClient()
    shares = await client.get_group_shares(group_id)
    if shares:
        table_data = [
            [
                click.style(share.id, fg="blue"),
                share.resource_type,
                click.style(share.resource_id, fg="green"),
                click.style(share.shared_by, fg="yellow"),
                share.shared_at,
            ]
            for share in shares
        ]
        click.echo(
            tabulate(
                table_data,
                headers=["ID", "Type", "Resource ID", "Shared By", "Shared At"],
                tablefmt="simple",
            )
        )
    else:
        click.echo(click.style("No shared resources found", fg="red"))


@share.command("add")
@click.argument("group_id")
@click.argument("resource_type")
@click.argument("resource_id")
@coro
async def add_share(group_id: str, resource_type: str, resource_id: str) -> None:
    """Share a resource with a group."""
    async with GroupClient() as client:
        share = await client.share_resource_with_group(group_id, resource_type, resource_id)
    click.echo("Resource shared:")
    click.echo(f"  ID: {click.style(share.id, fg='blue')}")
    click.echo(f"  Type: {share.resource_type}")
    click.echo(f"  Resource ID: {click.style(share.resource_id, fg='green')}")


@share.command("remove")
@click.argument("group_id")
@click.argument("share_id")
@click.confirmation_option(prompt="Are you sure you want to remove this share?")
@coro
async def remove_share(group_id: str, share_id: str) -> None:
    """Remove a resource share from a group."""
    async with GroupClient() as client:
        await client.unshare_resource_from_group(group_id, share_id)
    click.echo(f"Share removed: {click.style(share_id, fg='red')}")


if __name__ == "__main__":
    cli()
