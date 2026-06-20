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
        project_root_path: The root path of the project (Git repository).
            Used for binding .git directory as read-only.
        home_path: The home directory to hide. Defaults to the current user's
            home directory. Set to None to not hide any home directory.
        additional_mounts: Additional mounts to create in the jail. Order matters
            - later mounts override earlier ones.
        hide_home: Whether to hide the home directory.
        expose_path_entries: Whether to re-expose PATH entries from the hidden
            home directory as read-only.
    """

    workdir_path: pathlib.Path
    project_root_path: pathlib.Path | None = None
    home_path: pathlib.Path | None = None
    additional_mounts: list[MountSpec] = dataclasses.field(default_factory=list)
    hide_home: bool = True
    expose_path_entries: bool = True

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


@dataclasses.dataclass(frozen=True, kw_only=True)
class BwrapJail(Jail):
    """A jail that uses bubblewrap (bwrap) for sandboxing.

    This jail uses bubblewrap to provide a sandboxed environment with controlled
    filesystem access. By default, only the workdir is writable, and the
    following are accessible read-only:
    - Standard system paths (/usr, /etc, /lib, /lib64, /bin, /sbin)
    - The .git directory from the project root

    The home directory is hidden by default (replaced with a tmpfs), and PATH
    entries from the hidden home directory are re-exposed as read-only at their
    original paths.

    Requires bubblewrap (bwrap) to be installed and available in PATH.

    Raises:
        FileNotFoundError: If bwrap is not found in PATH.
    """

    def _get_home_path(self) -> pathlib.Path:
        """Get the home path to use for hiding."""
        if self.home_path is not None:
            return self.home_path
        return pathlib.Path.home()

    def _re_expose_path_entries(self, home: pathlib.Path) -> list[MountSpec]:
        """Re-expose PATH entries that are under home as read-only.

        Returns MountSpec objects for each PATH entry under home.

        For symlinks (like ~/.nix-profile), we resolve to the real path but
        bind to the original symlink path.

        Args:
            home: The home directory path.

        Returns:
            List of MountSpec objects for ro-bind mounts.
        """
        result: list[MountSpec] = []
        path_env = os.environ.get("PATH", "")

        for entry in path_env.split(":"):
            if not entry:
                continue
            entry_path = pathlib.Path(entry)
            if not entry_path.exists():
                continue
            try:
                # Check if the ORIGINAL entry path (before resolving symlinks) is under home
                # This handles cases like ~/.nix-profile which is a symlink
                try:
                    rel_path = entry_path.relative_to(home)
                    is_under_home = True
                except ValueError:
                    is_under_home = False

                if is_under_home:
                    # Resolve to the real path (following symlinks)
                    real_entry = entry_path.resolve()
                    # Bind the real path to the ORIGINAL entry path
                    result.append(
                        MountSpec(
                            mount_type=MountType.RO, source=real_entry, dest=entry_path
                        )
                    )
            except (OSError, RuntimeError):
                # If we can't resolve the path, skip it
                pass

        return result

    def _build_bwrap_args(self) -> list[str]:
        """Build the bwrap command line arguments.

        Returns:
            List of arguments for the bwrap command.
        """
        args: list[str] = [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
        ]

        # Bind everything as read-only from the root
        root = pathlib.Path("/")
        if root.exists():
            args.extend(["--ro-bind", "/", "/"])

        # Hide /home directory completely
        if self.hide_home:
            args.extend(["--tmpfs", "/home"])

        # Override with writable workdir
        args.extend(["--bind", str(self.workdir_path), str(self.workdir_path)])

        # Override /dev with device access
        args.extend(["--dev", "/dev"])

        # Override /proc with process filesystem
        args.extend(["--proc", "/proc"])

        # Override /tmp with a new tmpfs
        args.extend(["--tmpfs", "/tmp"])

        # Override /sys with tmpfs
        args.extend(["--tmpfs", "/sys"])

        # Project .git directory (ro)
        if self.project_root_path is not None:
            git_dir = self.project_root_path / ".git"
            if git_dir.exists():
                args.extend(["--ro-bind", str(git_dir), str(git_dir)])

        # Re-expose PATH entries from home as ro at their original paths
        if self.hide_home and self.expose_path_entries:
            home = self._get_home_path()
            path_mounts = self._re_expose_path_entries(home)
            for mount in path_mounts:
                args.extend(["--ro-bind", str(mount.source), str(mount.dest)])

        # Additional mounts (order matters - later overrides earlier)
        for mount in self.additional_mounts:
            if mount.mount_type == MountType.RO:
                args.extend(["--ro-bind", str(mount.source), str(mount.dest)])
            elif mount.mount_type == MountType.RW:
                args.extend(["--bind", str(mount.source), str(mount.dest)])
            elif mount.mount_type == MountType.TMPFS:
                args.extend(["--tmpfs", str(mount.dest)])
            elif mount.mount_type == MountType.DEV:
                args.extend(["--dev", str(mount.dest)])
            elif mount.mount_type == MountType.PROC:
                args.extend(["--proc", str(mount.dest)])

        return args

    def run(
        self, args: typing.Sequence[str] | None = None
    ) -> subprocess.CompletedProcess:
        """Run a shell session or command inside the bwrap sandbox.

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
            FileNotFoundError: If bwrap or the shell/command is not found.
        """
        # Check if bwrap is available
        bwrap_path = shutil.which("bwrap")
        if bwrap_path is None:
            message = "bwrap (bubblewrap) is not installed or not found in PATH"
            raise FileNotFoundError(message)

        bwrap_args = self._build_bwrap_args()

        if args is None:
            # Use default shell
            standard_shells = ["/bin/bash", "/bin/sh", "/usr/bin/bash", "/usr/bin/sh"]
            shell = None
            for s in standard_shells:
                if pathlib.Path(s).exists():
                    shell = s
                    break

            if not shell:
                shell = os.environ.get("SHELL")

            if not shell or not pathlib.Path(shell).exists():
                shell = shutil.which("bash") or shutil.which("sh")

            if not shell:
                message = "No shell binary available."
                raise FileNotFoundError(message)

            args = [shell]

        # Combine bwrap args with the command args
        full_args = bwrap_args + list(args)

        return subprocess.run(
            full_args,
            cwd=self.workdir_path,
            check=False,
            capture_output=False,
        )


class JailBackend(enum.Enum):
    """Enum for the different jail backends."""

    NONE = NoneJail
    BWRAP = BwrapJail
