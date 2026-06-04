"""CLI for Arborinth's `project` module.

This module provides the command-line interface for project-related operations.
"""

import typing

import click

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.group()
def project() -> None:
    """Manage an Arborinth project.

    A project is a top-level concept in Arborinth, closely related to a Git
    repository. Use these commands to inspect and manage a project.
    """


@project.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display information about the current project.

    Shows the Git repository root path and workspace root path for the project.
    """
    try:
        project: Project = ctx.obj
        click.echo(f"Project root: {project.repo_root_path}")
        click.echo(f"Workspace root: {project.workspace_root_path}")
    except RuntimeError as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc
