"""Arborinth shell module.

This module provides the functionality to run jailed shell sessions inside
workspaces.
"""

# ruff: noqa: F401 (unused-import)

from .logic import (
    BubblewrapJail,
    Jail,
    JailBackend,
    MountSpec,
    MountType,
    NoneJail,
    default_mount_specs,
)
from .preset import Preset, get_preset, list_presets
