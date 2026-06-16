"""Logic for the Arborinth's 'shell' module.

This module provides the core logic for running jailed shell sessions inside
workspaces.
"""

from __future__ import annotations

import abc
import dataclasses
import enum
import os
import shutil
import subprocess
import typing

if typing.TYPE_CHECKING:
    import pathlib


@dataclasses.dataclass(frozen=True, kw_only=True)
class Jail(abc.ABC):
    """Abstract base class for a jail.

    A jail is an environment that can run a shell session or command.

    Attributes:
        workdir_path: The directory to run commands in.
    """

    workdir_path: pathlib.Path

    @abc.abstractmethod
    def run(
        self, args: typing.Sequence[str] | None = None
    ) -> subprocess.CompletedProcess:
        """Run a shell session or command inside the jail's workdir.

        Args:
            args: The command to run.

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.
        """


@dataclasses.dataclass(frozen=True, kw_only=True)
class NoneJail(Jail):
    """A jail that does not actually jail the process.

    This does **not** jail the process in any way, it should only be used if you
    are absolutely sure that the command you are running is safe.

    The main purpose of this class is convenience, so that you can quickly run
    commands in the target directory without having to manually `cd` into it.
    For example, when you want to perform git operations in another repository.
    """

    def run(
        self, args: typing.Sequence[str] | None = None
    ) -> subprocess.CompletedProcess:
        """Start a shell session or run a command directly on the host.

        This does **not** jail the process in any way, it should only be used if
        you are absolutely sure that the command you are running is safe.

        If no args are provided, the default shell is used: the value of the
        `$SHELL` environment variable is attempted first with fallbacks to
        `bash` and `sh` (in that order). The shell binary must be found in the
        system `$PATH`.

        The process's stdout and stderr are not captured (allowing for
        interactive use) and the exit code is not checked.

        Args:
            args: The command to run.

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.

        Raises:
            FileNotFoundError: If the shell or command is not found in `$PATH`.
        """
        if args is None:
            shell = os.environ.get("SHELL")

            # If no default `$SHELL` is set, or if the shell binary is not
            # found, attempt to use `bash` or `sh` as a fallback.
            if not shell or shutil.which(shell) is None:
                shell = shutil.which("bash") or shutil.which("sh")

            # If there is no shell available (both `$SHELL` and fallbacks are
            # missing), raise an error.
            if not shell:
                message = "No shell binary available."
                raise FileNotFoundError(message)

            # Use the shell as the command to run.
            args = [shell]

        # Might raise `FileNotFoundError` if the command is not found.
        return subprocess.run(
            args,
            # Run the command in the jail's workdir.
            cwd=self.workdir_path,
            # Do not raise an exception if the command fails in order to
            # propagate the exit code.
            check=False,
            # Do not capture the output because the shell should be interactive.
            capture_output=False,
        )


class JailBackend(enum.Enum):
    """Enum for the different jail backends."""

    NONE = NoneJail
