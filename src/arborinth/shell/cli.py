"""CLI for Arborinth's `shell` module.

This module provides the command-line interface for shell-related operations.
"""

import typing

import click

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.command()
@click.pass_context
def shell(
    ctx: click.Context,
) -> None:
    """Run a shell in an isolated environment in a workspace."""
    project: Project = ctx.obj  # noqa: F841
