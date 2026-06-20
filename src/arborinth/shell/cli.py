"""CLI for Arborinth's `shell` module.

This module provides the command-line interface for shell-related operations.
"""

import sys
import typing

import click

from arborinth.shell import (
    JailBackend,
    JailConfig,
    MountSpec,
    mistral_vibe_preset,
    opencode_preset,
)

if typing.TYPE_CHECKING:
    from arborinth import Project


# Map preset names to factory functions
JAIL_PRESETS: dict[str, typing.Callable[[], JailConfig]] = {
    "mistral-vibe": mistral_vibe_preset,
    "opencode": opencode_preset,
}


@click.command()
@click.argument("workspace_name")
@click.argument("args", nargs=-1, required=False)
@click.option(
    "--jail",
    type=click.Choice(
        [jail.name.lower() for jail in JailBackend], case_sensitive=False
    ),
    callback=lambda ctx, param, value: JailBackend[value.upper()],  # noqa: ARG005
    default=JailBackend.NONE.name,
    show_default=True,
    help="Jail backend to use for isolation.",
)
@click.option(
    "--preset",
    type=click.Choice(list(JAIL_PRESETS.keys()), case_sensitive=False),
    default=None,
    help="Pre-configured jail preset (mistral-vibe, opencode).",
)
@click.option(
    "--mount",
    "mounts",
    multiple=True,
    help=(
        "Mount specification for the jail. Format: type:source[:dest]. "
        "Types: ro (read-only bind), rw (read-write bind), tmpfs, dev, proc. "
        "Examples: ro:/path/to/config, rw:/path/to/cache, tmpfs:/tmp/extra. "
        "Order matters - later mounts override earlier ones."
    ),
)
@click.option(
    "--hide-home/--no-hide-home",
    default=True,
    help="Hide the home directory in the jail.",
)
@click.option(
    "--expose-path/--no-expose-path",
    default=True,
    help="Re-expose PATH entries from the hidden home directory.",
)
@click.pass_context
def shell(
    ctx: click.Context,
    workspace_name: str,
    args: tuple[str, ...],
    jail: JailBackend,
    preset: str | None,
    mounts: tuple[str, ...],
    hide_home: bool,
    expose_path: bool,
) -> None:
    """Run a shell or command in a workspace.

    Opens an interactive shell session or executes a command in the specified
    workspace. The workspace must already exist in the project.

    If no command is specified (i.e., only the workspace name is provided),
    opens a shell session in the workspace's workdir using the default shell
    (from `$SHELL`, falling back to bash or sh).

    If a command is provided, executes that command in the workspace's workdir
    instead of opening a shell. The exit code of the command is propagated.

    Use --jail to select the isolation backend.
    Available backends: none (default, no isolation), bwrap (bubblewrap sandbox).

    Available presets: mistral-vibe, opencode.

    When using bwrap, you can configure additional mounts with --mount.
    Mount format: type:source[:dest] where type is ro, rw, tmpfs, dev, or proc.
    Order matters - later mounts override earlier ones.
    """
    project: Project = ctx.obj

    try:
        workspace = project.workspace(workspace_name)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    # Parse mount specifications
    additional_mounts: list[MountSpec] = []
    for spec in mounts:
        try:
            additional_mounts.append(MountSpec.from_spec(spec))
        except ValueError as exc:
            message = f"Invalid mount specification: {spec}. Expected format: type:source[:dest]"
            raise click.ClickException(message) from exc

    # Build jail config from preset + CLI options
    # Note: workdir_path will be set by workspace.shell() if not provided
    jail_config: JailConfig | None = None
    if preset is not None:
        # Start with preset config
        preset_func = JAIL_PRESETS[preset]
        jail_config = preset_func()
    else:
        # Start with empty config (workdir_path will be set by workspace)
        jail_config = JailConfig()

    # Merge CLI options into config
    cli_overrides = JailConfig(
        additional_mounts=additional_mounts,
        hide_home=hide_home,
        expose_path_entries=expose_path,
    )
    jail_config = jail_config | cli_overrides

    try:
        proc = workspace.shell(
            args=args or None,
            jail_backend=jail,
            jail_config=jail_config,
        )
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    # Propagate the exit code of the shell process.
    sys.exit(proc.returncode)
