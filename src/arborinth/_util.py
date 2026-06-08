"""Utility functions and descriptors for Arborinth.

This module provides validation utilities used across Arborinth.
"""

from __future__ import annotations

import string


def format_info(info: dict[str, str]) -> str:
    """Format a dictionary of object information into a string.

    This function is used to format the output of the `info` command for e.g.
    `arborinth project info` or `arborinth workspace info`.

    Args:
        info: A dictionary of information to format.

    Returns:
        A string representation of the information.
    """
    return "\n".join(f"{key.replace('_', ' ')}: {value}" for key, value in info.items())


def validate_workspace_name(name: str) -> None:
    r"""Validate a workspace name.

    Validation rules:
    - Cannot be empty
    - Cannot contain path separators (/ or \)
    - Cannot contain '..'
    - Cannot start with '.'
    - Cannot contain forbidden characters: <>:"|?*
    - Cannot contain whitespace

    Args:
        name: The workspace name to validate.

    Raises:
        ValueError: If the name violates any validation rule.
    """
    if not name:
        message = "Workspace name cannot be empty"
        raise ValueError(message)

    if "/" in name or "\\" in name:
        message = f"Workspace name cannot contain path separators: {name}"
        raise ValueError(message)

    if ".." in name:
        message = f"Workspace name cannot contain '..': {name}"
        raise ValueError(message)

    if name.startswith("."):
        message = f"Workspace name cannot start with '.': {name}"
        raise ValueError(message)

    forbidden_chars = '<>:"|?*'
    if any(c in name for c in forbidden_chars):
        message = f"Workspace name contains forbidden characters: {name}"
        raise ValueError(message)

    if any(c in name for c in string.whitespace):
        message = f"Workspace name cannot contain whitespace: {name}"
        raise ValueError(message)
