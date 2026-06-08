"""CLI for Arborinth's `project` module.

This module provides the command-line interface for project-related operations.
"""

import typing

import click

from arborinth import _util

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.group()
def project() -> None:
    """Manage an Arborinth project.

    A project is a top-level concept in Arborinth, closely related to a Git
    repository. Use these commands to inspect and manage a project.
    """


@project.command()
@_util.click_format_option
@click.pass_context
def info(ctx: click.Context, output_format: _util.InfoFormat) -> None:
    """Display information about the current project.

    Shows the Git repository root path and workspace root path for the project.
    """
    try:
        project: Project = ctx.obj
        click.echo(_util.format_info(project.info, output_format))
    except RuntimeError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc
