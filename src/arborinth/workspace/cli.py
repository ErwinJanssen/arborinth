"""CLI for Arborinth's `workspace` module.

This module provides the command-line interface for workspace-related operations.
"""

import typing

import click

from arborinth import _util

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.group()
def workspace() -> None:
    """Manage Arborinth workspaces.

    A workspace is an isolated clone of your repository where untrusted code
    can perform operations without affecting the original repository.
    """


@workspace.command()
@click.argument("name")
@click.pass_context
def create(ctx: click.Context, name: str) -> None:
    """Create a new workspace.

    Creates a new workspace with the given name in the project's workspace root
    directory.
    """
    try:
        project: Project = ctx.obj
        workspace = project.create_workspace(name)
        click.echo(f"Created workspace: {workspace.root_path}")
    except (RuntimeError, OSError) as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc


@workspace.command(name="list")
@click.pass_context
def list_(ctx: click.Context) -> None:
    """List workspaces for the project."""
    try:
        project: Project = ctx.obj
        workspaces = project.workspaces

        if not workspaces:
            click.echo("No workspaces found for this project.")
            return

        for ws in workspaces:
            click.echo(ws.name)
    except RuntimeError as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc


@workspace.command()
@click.argument("name")
@click.pass_context
def info(ctx: click.Context, name: str) -> None:
    """Display information about a workspace.

    Shows the workspace name, its root path, and the remote name in the
    original repository.
    """
    try:
        project: Project = ctx.obj
        workspace = project.workspace(name)
        click.echo(_util.format_info(workspace.info))
    except (RuntimeError, OSError) as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc


@workspace.command()
@click.argument("name")
@click.pass_context
def delete(ctx: click.Context, name: str) -> None:
    """Delete a workspace.

    Removes the workspace directory from the filesystem.
    """
    try:
        project: Project = ctx.obj
        workspace = project.workspace(name)
        workspace.delete()
        click.echo(f"Deleted workspace: {name}")
    except (RuntimeError, OSError) as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc
