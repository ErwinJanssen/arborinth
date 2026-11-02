"""Utility functions and descriptors for Arborinth.

This module provides validation and Git utilities used across Arborinth.
"""

from __future__ import annotations

import enum
import json
import os
import shutil
import string
import subprocess
import typing

import click

if typing.TYPE_CHECKING:
    import pathlib


def run_git(
    args: typing.Sequence[str],
    *,
    cwd: pathlib.Path | None = None,
    error_message: str | None = None,
    isolated: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command.

    By default the command runs with an environment isolated from the
    host system's Git configuration, and a failure raises `RuntimeError`
    with `error_message` as the prefix of its message. With `check=False`
    the result is returned instead, and failures are reported only through
    the return code, so callers that tolerate failure can ignore it. Pass
    `isolated=False` to inherit the environment of the current process,
    for commands that must read the host's Git configuration.

    Args:
        args: The arguments of the command, without the leading `git`.
        cwd: The directory to run the command in, or `None` for the
            current working directory.
        error_message: The prefix of the message of the `RuntimeError`
            raised when the command fails. A generic message is used when
            omitted.
        isolated: Whether to run the command with an environment
            isolated from the host system's Git configuration.
        check: Whether to raise `RuntimeError` when the command fails.

    Returns:
        The completed process, with its standard output and error
        captured.

    Raises:
        RuntimeError: If `check` is true and Git is not installed or the
            command fails.
    """
    env = (
        # An environment isolated from the host system's Git
        # configuration, for commands that must be reproducible and free
        # of host state, and that must not prompt interactively.
        {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }
        if isolated
        else None
    )
    prefix = error_message or "Failed to run Git"
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            check=check,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        message = f"{prefix}: {stderr}"
        raise RuntimeError(message) from exc
    except FileNotFoundError as exc:
        # The raw error distinguishes a missing Git installation from a
        # missing working directory.
        message = f"{prefix}: {exc}"
        raise RuntimeError(message) from exc


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


def read_commit_identity(repo_path: pathlib.Path) -> dict[str, str]:
    """Read the commit identity of a repository.

    The identity is read from the repository's effective configuration,
    which includes the host's Git configuration: it is the identity a commit
    in that repository would use.

    Args:
        repo_path: The root path of the repository.

    Returns:
        A dictionary of the `user.name` and `user.email` values that are
        configured, which may be partial or empty.
    """
    identity = {}
    for key in ("user.name", "user.email"):
        # `git config --get` exits with a non-zero status when the key is
        # not set, which is not an error here. The environment is
        # inherited rather than isolated: the identity is read from the
        # repository's effective configuration, which includes the
        # host's Git configuration.
        result = run_git(
            ["config", "--get", key],
            cwd=repo_path,
            check=False,
            isolated=False,
        )
        if result.returncode == 0:
            identity[key] = result.stdout.strip()
    return identity


def write_commit_identity(
    worktree_path: pathlib.Path,
    identity: dict[str, str],
    *,
    error_message: str,
) -> None:
    """Write a commit identity to a repository's local configuration.

    A fresh clone has no commit identity of its own: Git does not write
    `user.name` and `user.email` to a clone's local configuration, so
    commits in the clone depend on the surrounding Git configuration.
    Writing the identity to the clone's local configuration lets commits
    be created inside the clone without it.

    Args:
        worktree_path: The working tree of the clone to write to.
        identity: The identity to write, as returned by
            `read_commit_identity`. Nothing is written when the identity is
            incomplete, so a clone is never left with a partial identity.
        error_message: The prefix of the message of the `RuntimeError`
            raised when writing the identity fails.

    Raises:
        RuntimeError: If Git is not installed or writing the identity
            fails.
    """
    if len(identity) < 2:  # noqa: PLR2004
        return

    for key, value in identity.items():
        run_git(
            ["config", "--local", key, value],
            cwd=worktree_path,
            error_message=error_message,
        )
