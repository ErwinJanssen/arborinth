"""CLI for Arborinth's `shell` module.

This module provides the command-line interface for shell-related operations.
"""

import sys
import typing

import click

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.command()
@click.argument("workspace_name")
@click.argument("args", nargs=-1, required=False)
@click.pass_context
def shell(
    ctx: click.Context,
    workspace_name: str,
    args: tuple[str, ...],
) -> None:
    """Run a shell or command in a workspace.

    Opens an interactive shell session or executes a command in the specified
    workspace. The workspace must already exist in the project.

    If no command is specified (i.e., only the workspace name is provided),
    opens a shell session in the workspace's workdir using the default shell
    (from `$SHELL`, falling back to bash or sh).

    If a command is provided, executes that command in the workspace's workdir
    instead of opening a shell. The exit code of the command is propagated.
    """
    project: Project = ctx.obj

    try:
        workspace = project.workspace(workspace_name)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    try:
        proc = workspace.shell(args=args or None)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    # Propagate the exit code of the shell process.
    sys.exit(proc.returncode)
