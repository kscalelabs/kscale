"""Defines the CLI for managing permissions."""

import logging

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.permission import PermissionClient

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Manage user permissions."""
    pass


@cli.command("list-all")
@coro
async def list_all_permissions() -> None:
    """List all available permissions."""
    client = PermissionClient()
    permissions = await client.get_all_permissions()
    if permissions:
        table_data = [
            [
                click.style(perm.permission, fg="blue"),
                perm.description,
            ]
            for perm in permissions
        ]
        click.echo(
            tabulate(
                table_data,
                headers=["Permission", "Description"],
                tablefmt="simple",
            )
        )
    else:
        click.echo(click.style("No permissions found", fg="red"))


@cli.command()
@click.option("-u", "--user-id", type=str, default="me", help="User ID (default: me)")
@coro
async def list(user_id: str = "me") -> None:
    """List permissions for a user."""
    client = PermissionClient()
    user_perms = await client.get_user_permissions(user_id)

    click.echo(f"User: {click.style(user_perms.display_name, fg='green')} ({user_perms.email})")
    click.echo(f"User ID: {click.style(user_perms.user_id, fg='blue')}")
    click.echo(f"Status: {'Active' if user_perms.is_active else 'Inactive'}")
    click.echo("\nPermissions:")

    if user_perms.permissions:
        for perm in user_perms.permissions:
            click.echo(f"  • {click.style(perm, fg='yellow')}")
    else:
        click.echo(click.style("  No permissions assigned", fg="red"))


@cli.command()
@click.argument("user_id")
@click.argument("permissions", nargs=-1, required=True)
@coro
async def set(user_id: str, permissions: tuple[str, ...]) -> None:
    """Set permissions for a user (replaces all existing permissions)."""
    async with PermissionClient() as client:
        user_perms = await client.update_user_permissions(user_id, list(permissions))

    click.echo("Permissions updated:")
    click.echo(f"  User: {click.style(user_perms.display_name, fg='green')}")
    click.echo(f"  Permissions: {', '.join([click.style(p, fg='yellow') for p in user_perms.permissions])}")


@cli.command()
@click.argument("user_id")
@click.argument("permission")
@coro
async def add(user_id: str, permission: str) -> None:
    """Add a permission to a user."""
    async with PermissionClient() as client:
        user_perms = await client.add_user_permission(user_id, permission)

    click.echo("Permission added:")
    click.echo(f"  User: {click.style(user_perms.display_name, fg='green')}")
    click.echo(f"  Added: {click.style(permission, fg='yellow')}")
    click.echo(f"  All permissions: {', '.join([click.style(p, fg='yellow') for p in user_perms.permissions])}")


@cli.command()
@click.argument("user_id")
@click.argument("permission")
@coro
async def remove(user_id: str, permission: str) -> None:
    """Remove a permission from a user."""
    async with PermissionClient() as client:
        user_perms = await client.remove_user_permission(user_id, permission)

    click.echo("Permission removed:")
    click.echo(f"  User: {click.style(user_perms.display_name, fg='green')}")
    click.echo(f"  Removed: {click.style(permission, fg='red')}")
    click.echo(f"  Remaining permissions: {', '.join([click.style(p, fg='yellow') for p in user_perms.permissions])}")


if __name__ == "__main__":
    cli()
