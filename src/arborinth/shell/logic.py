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
import subprocess
import typing

from arborinth import _util


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

        # These mount types only support a destination path. If the source path
        # is not `None`, raise an error.
        if (
            mount_type in (MountType.TMPFS, MountType.DEV, MountType.PROC)
            and source_path_str is not None
        ):
            message = f"Mount type {mount_type} only supports a destination path"
            raise ValueError(message)

        # Convert the source and destination paths to `pathlib.Path` objects.
        source_path = pathlib.Path(source_path_str) if source_path_str else None
        destination_path = pathlib.Path(destination_path_str)

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
        tmp_path: Path to a scratch directory that jail backends that support
            mounts bind at `/tmp`. If `None`, the backend chooses its own
            default (e.g. an ephemeral tmpfs). The directory must exist when the
            jail is run.
        cache_path: Path to a cache directory that jail backends that support
            mounts bind at the user's cache directory (`XDG_CACHE_HOME`,
            default `~/.cache`). If `None`, no such bind is made. The
            directory must exist when the jail is run.
        home_path: Path to a directory that jail backends that support mounts
            bind at the user's home directory, masking the host home
            directory. If `None`, no such bind is made and the host home
            directory remains visible through the root bind. The directory
            must exist when the jail is run.
        mount_specs: Additional mount specifications for this jail.
    """

    workdir_path: pathlib.Path
    tmp_path: pathlib.Path | None = None
    cache_path: pathlib.Path | None = None
    home_path: pathlib.Path | None = None
    mount_specs: typing.Sequence[MountSpec] = ()

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

    Note:
        `tmp_path`, `cache_path`, `home_path` and `mount_specs` are accepted
        but ignored by this jail since it does not use any sandboxing.
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


@dataclasses.dataclass(frozen=True, kw_only=True)
class BubblewrapJail(Jail):
    """A jail that uses bubblewrap (bwrap) for sandboxing.

    This jail uses bubblewrap to provide a sandboxed environment with controlled
    filesystem access. It binds the entire host filesystem read-only by default,
    which means the sandboxed process can read any file on the host system.
    Only the working directory is bound read-write. If `tmp_path` is set, that
    directory is bound read-write at `/tmp`, otherwise a fresh tmpfs is used. If
    `cache_path` is set, that directory is bound read-write at the user's cache
    directory. If `home_path` is set, that directory is bound read-write at the
    user's home directory, masking the host home directory, and tool paths on
    `PATH` under it are bound read-only. `/run` is masked with a fresh tmpfs,
    so that host sockets are not reachable from the sandbox.

    Security note: This provides isolation but NOT security. A malicious process
    can still read sensitive files from the host.

    Requires bubblewrap (bwrap) to be installed and available in PATH.
    """

    @staticmethod
    def _mount_to_bwrap_args(mount: MountSpec) -> list[str]:
        """Convert a MountSpec to the corresponding bwrap arguments.

        Args:
            mount: The mount specification to convert.

        Returns:
            A list of bwrap arguments for this mount.
        """
        if mount.mount_type == MountType.RO:
            source = str(mount.source) if mount.source else str(mount.dest)
            return ["--ro-bind", source, str(mount.dest)]
        if mount.mount_type == MountType.RW:
            source = str(mount.source) if mount.source else str(mount.dest)
            return ["--bind", source, str(mount.dest)]
        if mount.mount_type == MountType.TMPFS:
            return ["--tmpfs", str(mount.dest)]
        if mount.mount_type == MountType.DEV:
            return ["--dev", str(mount.dest)]
        if mount.mount_type == MountType.PROC:
            return ["--proc", str(mount.dest)]
        return []

    @staticmethod
    def _run_mask_specs(
        run: pathlib.Path = pathlib.Path("/run"),
        resolv_conf: pathlib.Path = pathlib.Path("/etc/resolv.conf"),
    ) -> list[MountSpec]:
        """Return mount specs that mask the given runtime directory.

        The directory is replaced by a fresh tmpfs, so that files in it, such
        as host socket files, are not reachable from the sandbox.

        DNS is kept working when `resolv_conf` is a symlink into the masked
        directory, as on systems using systemd-resolved: the file it points to
        is bound read-only at its real location, so that the symlink inside the
        sandbox still resolves.

        Args:
            run: The runtime directory to mask.
            resolv_conf: The path of the resolver configuration.

        Returns:
            A list of mount specs.
        """
        specs = [MountSpec(mount_type=MountType.TMPFS, source=None, dest=run)]

        # The runtime directory of the user usually points into the masked
        # directory. Provide an empty one, because tools expect it to exist.
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if runtime_dir is not None and pathlib.Path(runtime_dir).is_relative_to(run):
            specs.append(
                MountSpec(
                    mount_type=MountType.TMPFS,
                    source=None,
                    dest=pathlib.Path(runtime_dir),
                )
            )

        # Keep DNS working when the resolver configuration is a symlink into
        # the masked directory, as on systems using systemd-resolved.
        if resolv_conf.is_symlink():
            target = resolv_conf.resolve()
            if target.is_relative_to(run):
                specs.append(
                    MountSpec(mount_type=MountType.RO, source=target, dest=target)
                )

        return specs

    @staticmethod
    def _tool_mount_specs(
        home: pathlib.Path, path_env: str | None = None
    ) -> list[MountSpec]:
        """Return read-only mount specs for tool paths under the home directory.

        When the home directory is masked, tools installed under it (e.g. in
        `~/.local/bin` or `~/.nix-profile/bin`) disappear from the sandbox.
        Each `PATH` entry under the home directory is made available again,
        read-only, by binding its parent directory: the entry `~/.local/bin`
        binds `~/.local`, so that support files next to the tools (e.g. in
        `~/.local/share`) remain available, and a project-local entry like
        `<project>/.venv/bin` binds only `<project>/.venv`, not the project
        directory above it. An entry directly under the home directory (e.g.
        `~/bin`) is bound itself, because its parent is the home directory,
        which is never bound. Entries whose parent directory does not exist
        are skipped.

        Args:
            home: The masked home directory to resolve tool paths against.
            path_env: The `PATH` environment variable value. Defaults to the
                current environment.

        Returns:
            A list of mount specs.
        """
        if path_env is None:
            path_env = os.environ.get("PATH", "")

        specs: list[MountSpec] = []
        for entry in path_env.split(os.pathsep):
            entry_path = pathlib.Path(entry)
            if not entry or entry_path == home or not entry_path.is_relative_to(home):
                continue
            # Bind the parent directory of the entry, so that support files
            # next to the tools remain available. The parent of an entry
            # directly under the home directory is the home directory itself,
            # which is never bound, so the entry is bound instead.
            bind_path = entry_path if entry_path.parent == home else entry_path.parent
            if not bind_path.is_dir():
                continue
            specs.append(
                MountSpec(mount_type=MountType.RO, source=bind_path, dest=bind_path)
            )
        return specs

    def build_command(
        self, args: typing.Sequence[str] | None = None
    ) -> typing.Sequence[str]:
        """Build the bwrap command line arguments.

        Args:
            args: The command to run. If None, the default shell is used.

        Returns:
            List of arguments for the bwrap command.
        """
        command = args or [_util.get_default_shell()]
        workdir_str = str(self.workdir_path.resolve())

        # The default mounts, in mount order. The scratch and cache
        # directories are mounted before the working directory, so that they
        # cannot shadow the working directory bind.
        mounts: list[MountSpec] = [
            # Bind the root filesystem read-only
            MountSpec(mount_type=MountType.RO, source=None, dest=pathlib.Path("/")),
            # Provide private /dev and /proc
            MountSpec(mount_type=MountType.DEV, source=None, dest=pathlib.Path("/dev")),
            MountSpec(
                mount_type=MountType.PROC, source=None, dest=pathlib.Path("/proc")
            ),
        ]

        # Mask `/run`, so that host sockets (such as the ssh-agent and D-Bus)
        # are not reachable from the sandbox.
        mounts.extend(self._run_mask_specs())

        # Mask the user's home directory: it is replaced by the workspace home
        # directory, so that files in it (e.g. SSH keys and configuration) are
        # not reachable from the sandbox. Tool paths on `PATH` under it are
        # bound read-only, so that tools remain available. The home mount comes
        # before the cache and working directory binds, so that it cannot
        # shadow them.
        if self.home_path is not None:
            home = pathlib.Path.home()
            mounts.append(
                MountSpec(mount_type=MountType.RW, source=self.home_path, dest=home)
            )
            mounts.extend(self._tool_mount_specs(home))

        # Mount `/tmp`: the scratch directory if one is configured, otherwise
        # a fresh tmpfs.
        if self.tmp_path is None:
            mounts.append(
                MountSpec(
                    mount_type=MountType.TMPFS,
                    source=None,
                    dest=pathlib.Path("/tmp"),  # noqa: S108
                )
            )
        else:
            mounts.append(
                MountSpec(
                    mount_type=MountType.RW,
                    source=self.tmp_path,
                    dest=pathlib.Path("/tmp"),  # noqa: S108
                )
            )

        # Bind the cache directory at the user's cache directory: if
        # `XDG_CACHE_HOME` is set, that directory is used, otherwise `~/.cache`.
        if self.cache_path is not None:
            cache_dest = os.environ.get("XDG_CACHE_HOME") or str(
                pathlib.Path.home() / ".cache"
            )
            mounts.append(
                MountSpec(
                    mount_type=MountType.RW,
                    source=self.cache_path,
                    dest=pathlib.Path(cache_dest),
                )
            )

        # Bind the working directory read-write
        mounts.append(
            MountSpec(
                mount_type=MountType.RW,
                source=pathlib.Path(workdir_str),
                dest=pathlib.Path(workdir_str),
            )
        )

        bwrap_args: list[str] = [
            "bwrap",
            # Unshare all namespaces for proper isolation
            "--unshare-all",
            # Retain the network namespace to allow network access
            "--share-net",
            # Set working directory inside the sandbox
            "--chdir",
            workdir_str,
        ]

        # Add the default mounts, followed by the user-specified mounts
        for mount in [*mounts, *self.mount_specs]:
            bwrap_args.extend(self._mount_to_bwrap_args(mount))

        return [
            *bwrap_args,
            # Separator between bwrap options and the command to run
            "--",
            # Add the command to execute
            *command,
        ]


class JailBackend(enum.Enum):
    """Enum for the different jail backends."""

    NONE = NoneJail
    BUBBLEWRAP = BubblewrapJail
