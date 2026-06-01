"""CLI for Arborinth's `project` module.

This module provides the command-line interface for project-related operations.
"""

import pathlib

import click

from . import logic


@click.group()
def project() -> None:
    """Manage an Arborinth project.

    A project is a top-level concept in Arborinth, closely related to a Git
    repository. Use these commands to inspect and manage a project.
    """


@project.command()
@click.option(
    "--workdir",
    "-C",
    type=click.Path(file_okay=False, dir_okay=True, path_type=pathlib.Path),
    default=".",
    help="Working directory within the Git repository.",
)
def info(workdir: pathlib.Path) -> None:
    """Display information about the current project.

    Shows the Git repository root path and workspace root path for the project.
    """
    try:
        project = logic.Project(workdir=workdir)
        click.echo(f"Project root: {project.repo_root_path}")
        click.echo(f"Workspace root: {project.workspace_root_path}")
    except (ValueError, RuntimeError) as exc:
        message = f"Error: {exc}"
        raise click.ClickException(message) from exc
