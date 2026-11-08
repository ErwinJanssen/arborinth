"""Logic for the Arborinth's 'workspace' concept.

This module contains the core `Workspace` class which represents an isolated
workspace derived from a Git repository. Workspaces are clones of the original
repository where untrusted code can make changes without affecting the original
repository.
"""

from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import shutil
import stat
import typing

from arborinth import _util
from arborinth.shell import JailBackend, MountSpec

if typing.TYPE_CHECKING:
    import subprocess

    from arborinth import Project


def _rmtree(path: pathlib.Path) -> None:
    """Remove a directory tree, including read-only directories.

    A process run inside a workspace can create read-only directories, for
    example a tool that marks the files it installs immutable. `shutil.rmtree`
    cannot remove the entries of a directory without write permission on that
    directory, so on a `PermissionError` the owner permission bits are restored
    on the failing directory and its parent, and the failed operation is
    retried. Any other error is raised unchanged.

    Args:
        path: The directory tree to remove.

    Raises:
        OSError: If the tree cannot be removed.
    """

    def onexc(
        func: typing.Callable[..., typing.Any],
        failed_path: str,
        exc: BaseException,
    ) -> None:
        if not isinstance(exc, PermissionError):
            raise exc
        failed = pathlib.Path(failed_path)
        for target in (failed, failed.parent):
            with contextlib.suppress(OSError):
                mode = target.lstat().st_mode
                if stat.S_ISDIR(mode):
                    target.chmod(stat.S_IMODE(mode) | stat.S_IRWXU)
        func(failed_path)

    shutil.rmtree(path, onexc=onexc)


@dataclasses.dataclass
class Workspace:
    """An isolated workspace for untrusted code execution.

    A workspace contains a clone of a Git repository (in the `workdir`
    subdirectory) where untrusted code can perform operations without affecting
    the original repository.

    Attributes:
        name: The name of the workspace.
        project: The Arborinth `Project` associated with the original repository.
    """

    name: str
    project: Project

    def __post_init__(self) -> None:
        """Validate the workspace after initialization.

        Raises:
            ValueError: If the workspace name is invalid.
            FileNotFoundError: If the workspace directory does not exist.
        """
        _util.validate_workspace_name(self.name)

        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)

    @property
    def root_path(self) -> pathlib.Path:
        """Path to this specific workspace directory.

        Returns:
            The absolute path to the workspace directory.
        """
        return self.project.workspace_root_path / self.name

    @property
    def workdir_path(self) -> pathlib.Path:
        """Path to the workdir (Git repository clone) within this workspace.

        Returns:
            The absolute path to the workspace's workdir directory, which
            contains the cloned Git repository.
        """
        return self.root_path / "workdir"

    @property
    def tmp_path(self) -> pathlib.Path:
        """Path to the tmp (scratch) directory within this workspace.

        The scratch directory holds disposable data for commands run in this
        workspace and is mounted read-write at `/tmp` inside jail backends that
        support mounts.

        Returns:
            The absolute path to the workspace's tmp directory.
        """
        return self.root_path / "tmp"

    @property
    def cache_path(self) -> pathlib.Path:
        """Path to the cache directory within this workspace.

        The cache directory holds disposable cached data (e.g. package manager
        caches) for commands run in this workspace and is bound read-write at
        the user's cache directory inside jail backends that support mounts.

        Returns:
            The absolute path to the workspace's cache directory.
        """
        return self.root_path / "cache"

    @property
    def home_path(self) -> pathlib.Path:
        """Path to the home directory within this workspace.

        The home directory holds per-workspace home state (e.g. tool
        configuration) for commands run in this workspace and is bound
        read-write at the user's home directory inside jail backends that
        support mounts, masking the host home directory.

        Returns:
            The absolute path to the workspace's home directory.
        """
        return self.root_path / "home"

    @property
    def remote_name(self) -> str:
        """Name of the remote in the original repository.

        Returns:
            The namespaced remote name: `arborinth/<workspace_name>`.
        """
        return f"arborinth/{self.name}"

    @property
    def info(self) -> dict[str, str]:
        """Workspace information as a dictionary.

        Returns:
            A dictionary containing workspace name, path, and remote name.
        """
        return {
            "workspace_name": self.name,
            "path": str(self.root_path),
            "remote": self.remote_name,
        }

    def register_as_remote(self) -> None:
        """Register this workspace as a remote in the original repository.

        Adds a git remote named `arborinth/<workspace_name>` pointing to the
        workspace's clone directory in the original repository. The remote
        uses a path relative to the repository root, so that it keeps working
        when the repository directory is moved.

        Raises:
            RuntimeError: If registering the remote fails.
        """
        relative = os.path.relpath(self.workdir_path, self.project.repo_root_path)

        _util.run_git(
            ["remote", "add", self.remote_name, relative],
            cwd=self.project.repo_root_path,
            error_message=(
                f"Failed to register remote '{self.remote_name}' in the "
                f"original repository"
            ),
        )

    def set_relative_origin_url(self) -> None:
        """Set the clone's `origin` remote URL to a relative path.

        Git stores the absolute path of the cloned repository as the clone's
        `origin` URL. This replaces it with a path relative to the clone, so
        that the workspace keeps working when the repository directory is
        moved. Relative paths in remote URLs are resolved against the
        repository root, so the URL works regardless of the directory a Git
        command is run from.

        Raises:
            RuntimeError: If setting the URL fails.
        """
        relative = os.path.relpath(self.project.repo_root_path, self.workdir_path)

        _util.run_git(
            ["remote", "set-url", "origin", relative],
            cwd=self.workdir_path,
            error_message=(f"Failed to set the origin URL for workspace '{self.name}'"),
        )

    def seed_commit_identity(self) -> None:
        """Seed the commit identity from the original repository into the clone.

        A fresh clone has no commit identity of its own: Git does not write
        `user.name` and `user.email` to a clone's local configuration, so
        commits in the workspace depend on the surrounding Git configuration.
        The identity of the original repository is written to the clone's
        local configuration, so that commits can be created inside the
        workspace without it. If the original repository has no identity
        configured, the clone is left unchanged.

        Raises:
            RuntimeError: If seeding the identity fails.
        """
        identity = {}
        for key in ("user.name", "user.email"):
            # `git config --get` exits with a non-zero status when the key
            # is not set, which is not an error here. The environment is
            # inherited rather than isolated: the identity to seed is the
            # one the user commits with, which may live in the host's
            # global Git configuration.
            result = _util.run_git(
                ["config", "--get", key],
                cwd=self.project.repo_root_path,
                check=False,
                isolated=False,
            )
            if result.returncode == 0:
                identity[key] = result.stdout.strip()

        if len(identity) < 2:  # noqa: PLR2004
            return

        for key, value in identity.items():
            _util.run_git(
                ["config", "--local", key, value],
                cwd=self.workdir_path,
                error_message=(
                    f"Failed to seed the commit identity for workspace '{self.name}'"
                ),
            )

    def unregister_as_remote(self) -> None:
        """Unregister this workspace's remote from the original repository.

        Removes the git remote named `arborinth/<workspace_name>` from the
        original repository.

        Silently ignores errors if the remote doesn't exist or git is
        unavailable.
        """
        # Ignore a missing remote and Git being unavailable.
        with contextlib.suppress(RuntimeError):
            _util.run_git(
                ["remote", "remove", self.remote_name],
                cwd=self.project.repo_root_path,
                check=False,
            )

    def delete(self) -> None:
        """Delete this workspace.

        Removes the workspace directory from the filesystem, including all its
        contents. Read-only directories inside the workspace are removed as
        well: a process run in the workspace may have created them, and a plain
        `shutil.rmtree` would fail on them with `Permission denied`. Also
        removes the corresponding remote from the original repository if it
        exists.

        Raises:
            FileNotFoundError: If the workspace directory does not exist.
            OSError: If the directory cannot be removed.
        """
        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)

        self.unregister_as_remote()

        _rmtree(self.root_path)

    def shell(
        self,
        args: typing.Sequence[str] | None = None,
        *,
        jail_backend: JailBackend = JailBackend.NONE,
        mount_specs: typing.Sequence[MountSpec] = (),
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a shell or command in this workspace with the specified jail backend.

        This opens a shell session or runs a command in the workspace's workdir
        with the specified jail backend. If `args` is `None`, the jail's default
        behavior is used.

        The command is executed in the workspace's workdir directory, which
        contains the cloned Git repository. The process's stdout and stderr are
        not captured, allowing for interactive use.

        The workspace's scratch directory (`tmp_path`), cache directory
        (`cache_path`) and home directory (`home_path`) are created if they do
        not exist and passed to the jail.

        Args:
            args: The command and arguments to run. If `None`, runs the default
                shell.
            jail_backend: The jail backend to use.
            mount_specs: Additional mount specifications to pass to the jail.
            env: Additional environment variables for the process, merged over
                the current environment. If `None`, the environment is
                inherited unchanged.

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.
        """
        # The scratch directory is created on demand.
        self.tmp_path.mkdir(exist_ok=True)

        # The cache directory is created on demand.
        self.cache_path.mkdir(exist_ok=True)

        # The home directory is created on demand.
        self.home_path.mkdir(exist_ok=True)

        return jail_backend.value(
            workdir_path=self.workdir_path,
            tmp_path=self.tmp_path,
            cache_path=self.cache_path,
            home_path=self.home_path,
            mount_specs=mount_specs,
        ).run(args=args, env=env)
