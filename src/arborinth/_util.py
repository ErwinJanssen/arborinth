"""Utility functions and descriptors for Arborinth.

This module provides validation utilities used across Arborinth.
"""

from __future__ import annotations

import enum
import json
import os
import shutil
import string

import click


class InfoFormat(enum.Enum):
    """Format for the info command."""

    TEXT = "text"
    JSON = "json"


# Click option decorator for adding `--format/` option to commands.
#
# This is defined here in order to reuse the same option across multiple
# commands (e.g. `arborinth project info` and `arborinth workspace info`).
click_format_option = click.option(
    "--format",
    "-f",
    # This sets the variable name that will be passed to the function, to avoid
    # shadowing the `format` builtin.
    "output_format",
    help="Output format.",
    show_default=True,
    # Use the `InfoFormat` enum to define the choices, set the default and
    # convert the input value to an `InfoFormat` enum member.
    type=click.Choice([output_format.value for output_format in InfoFormat]),
    default=InfoFormat.TEXT.value,
    callback=lambda ctx, param, value: InfoFormat(value),  # noqa: ARG005
)


def format_info(
    info: dict[str, str], output_format: InfoFormat = InfoFormat.TEXT
) -> str:
    """Format a dictionary of object information into a string.

    This function is used to format the output of the `info` command for e.g.
    `arborinth project info` or `arborinth workspace info`.

    Args:
        info: A dictionary of information to format.
        output_format: The format to use for the output.

    Returns:
        A string representation of the information.
    """
    if output_format == InfoFormat.TEXT:
        return "\n".join(
            f"{key.replace('_', ' ')}: {value}" for key, value in info.items()
        )

    if output_format == InfoFormat.JSON:
        return json.dumps(info)

    message = f"Unknown format: {output_format}"
    raise ValueError(message)


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


def get_default_shell() -> str:
    """Return the path to the default shell for the current user.

    The function attempts to determine the default shell in the following order:
    1. The value of the `$SHELL` environment variable (if set and executable)
    2. The `bash` binary (if found in `$PATH`)
    3. The `sh` binary (if found in `$PATH`)

    Returns:
        The absolute path to the shell binary.

    Raises:
        FileNotFoundError: If no shell binary is available on the system.
    """
    shell: str | None = None

    # First, try the $SHELL environment variable
    env_shell = os.environ.get("SHELL")
    if env_shell:
        shell = shutil.which(env_shell)

    # If $SHELL is not set or the binary doesn't exist, try fallbacks
    if not shell:
        shell = shutil.which("bash") or shutil.which("sh")

    if not shell:
        message = "No shell binary available."
        raise FileNotFoundError(message)

    return shell
