"""CLI for Arborinth's `workspace` module.

This module provides the command-line interface for workspace-related operations.
"""

import pathlib

import click

from arborinth import Project


@click.group()
def workspace() -> None:
    """Manage Arborinth workspaces.

    A workspace is an isolated clone of your repository where untrusted code
    can perform operations without affecting the original repository.
    """


@workspace.command()
@click.argument("name")
@click.option(
    "--workdir",
    "-C",
    type=click.Path(file_okay=False, dir_okay=True, path_type=pathlib.Path),
    default=".",
    help="Working directory within the Git repository.",
)
def create(workdir: pathlib.Path, name: str) -> None:
    """Create a new workspace.

    Creates a new workspace with the given name in the project's workspace root
    directory.
    """
    try:
        project = Project(workdir=workdir)
        workspace = project.create_workspace(name)
        click.echo(f"Created workspace: {workspace.root_path}")
    except (ValueError, RuntimeError, OSError) as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc
