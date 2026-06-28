"""CLI for Arborinth's `shell` module.

This module provides the command-line interface for shell-related operations.
"""

import shlex
import sys
import typing

import click

from arborinth.shell import JailBackend, MountSpec, get_preset, list_presets

if typing.TYPE_CHECKING:
    from arborinth import Project


class MountSpecParamType(click.ParamType):
    """Click parameter type for converting mount spec strings to MountSpec objects."""

    name = "mountspec"

    def convert(
        self,
        value: str,
        param: click.Parameter | None,  # noqa: ARG002
        ctx: click.Context | None,  # noqa: ARG002
    ) -> MountSpec:
        """Convert a mount spec string to a MountSpec object."""
        try:
            return MountSpec.from_spec(value)
        except ValueError as exc:
            self.fail(str(exc))


class PresetParamType(click.ParamType):
    """Click parameter type for looking up preset configurations by name."""

    name = "preset"

    def convert(
        self,
        value: str,
        param: click.Parameter | None,  # noqa: ARG002
        ctx: click.Context | None,  # noqa: ARG002
    ) -> object:
        """Look up a preset by name and return the ``Preset``."""
        try:
            return get_preset(value)
        except KeyError:
            available = ", ".join(list_presets())
            self.fail(f"Unknown preset '{value}'. Available presets: {available}")


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
@click.option(
    "--mount",
    type=MountSpecParamType(),
    multiple=True,
    help=(
        "Mount specification (e.g. ro:/src:/dest, tmpfs:/tmp)."
        " Can be specified multiple times."
    ),
)
@click.option(
    "--preset",
    type=PresetParamType(),
    multiple=True,
    help=(
        "A named preset that contributes mounts and an optional default command."
        " Can be specified multiple times."
    ),
)
@click.pass_context
def shell(  # noqa: PLR0913
    ctx: click.Context,
    workspace_name: str,
    args: tuple[str, ...],
    jail: JailBackend,
    mount: tuple[MountSpec, ...],
    preset: tuple[object, ...],
) -> None:
    """Run a shell or command in a workspace.

    Opens an interactive shell session or executes a command in the specified
    workspace. The workspace must already exist in the project.

    If no command is specified (i.e., only the workspace name is provided),
    opens a shell session in the workspace's workdir using the default shell
    (from `$SHELL`, falling back to bash or sh). If a ``--preset`` is used and
    no command is given, the preset's default command (if any) is executed
    instead of the shell.

    If a command is provided, executes that command in the workspace's workdir
    instead of opening a shell. The exit code of the command is propagated.

    Use --jail to select the isolation backend. Available backends:
    -   none (no isolation, run directly in the host)
    -   bubblewrap (bubblewrap sandbox)
    """
    project: Project = ctx.obj

    # Resolve presets and collect their mounts.
    preset_objects = list(preset)
    preset_mounts: list[MountSpec] = [m for p in preset_objects for m in p.mount_specs]

    # If no command was given on the CLI, use the first preset's default_command.
    command_args: tuple[str, ...] | None = args or None
    if not command_args and preset_objects:
        first = next((p for p in preset_objects if p.default_command), None)
        if first is not None:
            command_args = tuple(shlex.split(first.default_command))

    try:
        workspace = project.workspace(workspace_name)
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    try:
        proc = workspace.shell(
            args=command_args,
            jail_backend=jail,
            mount_specs=[*preset_mounts, *mount],
        )
    except FileNotFoundError as exc:
        message = str(exc)
        raise click.ClickException(message) from exc

    # Propagate the exit code of the shell process.
    sys.exit(proc.returncode)
