"""Logic for the Arborinth's 'shell' module.

This module provides the core logic for running jailed shell sessions inside
workspaces.
"""

from __future__ import annotations

import abc
import dataclasses
import enum
import os
import pathlib
import shutil
import subprocess
import typing


class MountType(enum.Enum):
    """Types of mounts supported in a jail.

    Attributes:
        RO: Read-only bind mount.
        RW: Read-write bind mount.
        TMPFS: Tmpfs mount.
        DEV: /dev mount.
        PROC: /proc mount.
    """

    RO = "ro"
    RW = "rw"
    TMPFS = "tmpfs"
    DEV = "dev"
    PROC = "proc"


@dataclasses.dataclass(frozen=True, kw_only=True)
class MountSpec:
    """Specification for a mount in a jail.

    This is used to configure mounts in a jail. The jail itself will handle
    the actual mounting, if supported by the jail type.

    Attributes:
        mount_type: Type of mount, see `MountType`.
        source: Source path for bind mounts. For mount types that do not require
            a source (e.g. `/proc` and `/dev`) this field is ignored. For bind
            mounts, this is the path to the source directory or file, if
            omitted, the destination path will be used as the source.
        dest: Destination path inside the jail.
    """

    mount_type: MountType
    source: pathlib.Path | None
    dest: pathlib.Path

    @classmethod
    def from_spec(cls, spec: str) -> typing.Self:
        """Parse a mount specification string.

        Supported formats:
        - ro:dest (ro-bind with same source and dest path)
        - rw:dest (rw-bind with same source and dest path)
        - ro:source:dest (ro-bind source to dest)
        - rw:source:dest (rw-bind source to dest)
        - tmpfs:dest (tmpfs mount)
        - dev:dest (devfs mount, usually `/dev`)
        - proc:dest (procfs mount, usually `/proc`)

        Args:
            spec: The mount specification string.

        Returns:
            A MountSpec instance.

        Raises:
            ValueError: If the spec format is invalid.
        """
        # Split the spec into parts.
        parts = spec.split(":")

        # Validate the number of parts, if there are too few or too many parts,
        # raise an error.
        if len(parts) < 2:  # noqa: PLR2004
            message = f"Invalid mount spec, too few parts: {spec}"
            raise ValueError(message)

        if len(parts) > 3:  # noqa: PLR2004
            message = f"Invalid mount spec, too many parts: {spec}"
            raise ValueError(message)

        # To simplify the logic below, if the spec is missing a source path,
        # insert `None` as the source path.
        if len(parts) == 2:  # noqa: PLR2004
            parts.insert(1, None)

        # Unpack the parts into variables.
        mount_type_str, source_path_str, destination_path_str = parts

        # Validate the mount type. If the mount type is invalid, raise an error.
        try:
            mount_type = MountType(mount_type_str)
        except ValueError:
            message = f"Invalid mount type: {mount_type_str}"
            raise ValueError(message) from None

        # Convert the source and destination paths to `pathlib.Path` objects.
        source_path = pathlib.Path(source_path_str) if source_path_str else None
        destination_path = pathlib.Path(destination_path_str)

        # These mount types only support a destination path. If the source path
        # is not `None`, raise an error.
        if (
            mount_type in (MountType.TMPFS, MountType.DEV, MountType.PROC)
            and source_path is not None
        ):
            message = f"Mount type {mount_type} only supports a destination path"
            raise ValueError(message)

        # At this point, the mount type is valid and the source and destination
        # paths are valid. Return the parsed mount spec.
        return cls(
            mount_type=mount_type,
            source=source_path,
            dest=destination_path,
        )


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
        shell is used.

        Args:
            args: The command to run.

        Returns:
            The command to pass to self.run().
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

        return args


class JailBackend(enum.Enum):
    """Enum for the different jail backends."""

    NONE = NoneJail
