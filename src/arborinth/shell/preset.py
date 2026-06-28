"""Preset configurations for jail mounts.

Presets provide named collections of mount specifications and default commands
that can be applied via the ``--preset`` CLI option.
"""

from __future__ import annotations

import dataclasses
import pathlib

from .logic import MountSpec, MountType

_HOME = pathlib.Path.home()


@dataclasses.dataclass(frozen=True)
class Preset:
    """A named preset that bundles mount specs with an optional default command.

    Attributes:
        name: The preset name used on the CLI.
        default_command: Command to run when no positional args are given.
        mount_specs: Mount specifications that the preset contributes.
    """

    name: str
    default_command: str | None = None
    mount_specs: tuple[MountSpec, ...] = ()


BUILTIN_PRESETS: dict[str, Preset] = {
    "opencode": Preset(
        name="opencode",
        default_command="opencode",
        mount_specs=(
            MountSpec(
                mount_type=MountType.RO,
                source=_HOME / ".config" / "opencode",
                dest=_HOME / ".config" / "opencode",
            ),
            MountSpec(
                mount_type=MountType.RW,
                source=_HOME / ".cache" / "opencode",
                dest=_HOME / ".cache" / "opencode",
            ),
            MountSpec(
                mount_type=MountType.RW,
                source=_HOME / ".local" / "share" / "opencode",
                dest=_HOME / ".local" / "share" / "opencode",
            ),
            MountSpec(
                mount_type=MountType.RW,
                source=_HOME / ".local" / "state" / "opencode",
                dest=_HOME / ".local" / "state" / "opencode",
            ),
        ),
    ),
}


def get_preset(name: str) -> Preset:
    """Look up a preset by name.

    Args:
        name: The preset name.

    Returns:
        The matching ``Preset``.

    Raises:
        KeyError: If no preset with that name exists.
    """
    if name not in BUILTIN_PRESETS:
        available = ", ".join(sorted(BUILTIN_PRESETS))
        msg = f"Unknown preset '{name}'. Available presets: {available}"
        raise KeyError(msg)
    return BUILTIN_PRESETS[name]


def list_presets() -> list[str]:
    """Return the names of all available presets."""
    return sorted(BUILTIN_PRESETS)
