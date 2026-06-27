"""Logic for the Arborinth's 'shell' module.

This module provides the core logic for running jailed shell sessions inside
workspaces.
"""

from __future__ import annotations

import abc
import dataclasses
import enum
import subprocess
import typing

from arborinth import _util

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

    def run(
        self, args: typing.Sequence[str] | None = None
    ) -> subprocess.CompletedProcess:
        """Run a shell session or command inside the jail's workdir.

        The process's stdout and stderr are not captured (allowing for
        interactive use) and the exit code is not checked.

        Args:
            args: The command to run. If no args are provided, the default shell
                is used (see `arborinth._util.get_default_shell()` for
                resolution order).

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.

        Raises:
            FileNotFoundError: If the shell or command is not found in `$PATH`.
        """
        command = self.build_command(args)

        # Might raise `FileNotFoundError` if the command is not found.
        return subprocess.run(
            command,
            # Run the command in the jail's workdir.
            cwd=self.workdir_path,
            # Do not raise an exception if the command fails in order to
            # propagate the exit code.
            check=False,
            # Do not capture the output because the shell should be interactive.
            capture_output=False,
        )

    @abc.abstractmethod
    def build_command(
        self, args: typing.Sequence[str] | None = None
    ) -> typing.Sequence[str]:
        """Build the command that will be executed by `run()`.

        This method is useful if you want to run the command in a different way
        than the default `run()` method. The implementation of this method
        depends heavily on the jail type.

        Args:
            args: The dynamic arguments that will be passed to the command.

        Returns:
            The command to run in a list of strings.
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

        If no args are provided, the default shell is used (see
        `arborinth._util.get_default_shell()` for resolution order).

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
        command = self.build_command(args)

        # Might raise `FileNotFoundError` if the command is not found.
        return subprocess.run(
            command,
            # Run the command in the jail's workdir.
            cwd=self.workdir_path,
            # Do not raise an exception if the command fails in order to
            # propagate the exit code.
            check=False,
            # Do not capture the output because the shell should be interactive.
            capture_output=False,
        )

    def build_command(
        self, args: typing.Sequence[str] | None = None
    ) -> typing.Sequence[str]:
        """Build the command to pass to self.run().

        If args is not `None`, it is returned as-is. Otherwise, the default
        shell is used (via `arborinth._util.get_default_shell()`).

        Args:
            args: The command to run.

        Returns:
            The command to pass to self.run().
        """
        return args if args is not None else [_util.get_default_shell()]


class JailBackend(enum.Enum):
    """Enum for the different jail backends."""

    NONE = NoneJail
