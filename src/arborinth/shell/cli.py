"""CLI for Arborinth's `shell` module.

This module provides the command-line interface for shell-related operations.
"""

import sys
import typing

import click

from arborinth.shell import JailBackend

if typing.TYPE_CHECKING:
    from arborinth import Project


@click.command()
@click.argument("workspace_name")
@click.argument("args", nargs=-1, required=False)
@click.option(
    "--jail",
    type=click.Choice(
        [jail.name.lower() for jail in JailBackend], case_sensitive=False
    ),
    callback=lambda ctx, param, value: JailBackend[value.upper()],  # noqa: ARG005
    default=JailBackend.NONE.name.lower(),
    show_default=True,
    help="Jail backend to use for isolation.",
)
@click.pass_context
def shell(
    ctx: click.Context,
    workspace_name: str,
    args: tuple[str, ...],
    jail: JailBackend,
) -> None:
    """Run a shell or command in a workspace.

    Opens an interactive shell session or executes a command in the specified
    workspace. The workspace must already exist in the project.

    If no command is specified (i.e., only the workspace name is provided),
    opens a shell session in the workspace's workdir using the default shell
    (from `$SHELL`, falling back to bash or sh).

    If a command is provided, executes that command in the workspace's workdir
    instead of opening a shell. The exit code of the command is propagated.

    Use --jail to select the isolation backend. Available backends:
    -   none (no isolation, run directly in the host)
    -   bubblewrap (bubblewrap sandbox)
    """
    project: Project = ctx.obj

    try:
        workspace = project.workspace(workspace_name)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    try:
        proc = workspace.shell(args=args or None, jail_backend=jail)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    # Propagate the exit code of the shell process.
    sys.exit(proc.returncode)
