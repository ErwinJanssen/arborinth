"""Logic for the Arborinth's 'workspace' concept.

This module contains the core `Workspace` class which represents an isolated
workspace derived from a Git repository. Workspaces are clones of the original
repository where untrusted code can make changes without affecting the original
repository.
"""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
import typing

from arborinth import _util
from arborinth.shell import JailBackend, JailConfig, MountSpec

if typing.TYPE_CHECKING:
    import pathlib

    from arborinth import Project


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
        workspace's clone directory in the original repository.

        Raises:
            RuntimeError: If registering the remote fails.
        """
        try:
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    self.remote_name,
                    str(self.workdir_path),
                ],
                cwd=self.project.repo_root_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            message = (
                f"Failed to register remote '{self.remote_name}' in original repository: "  # noqa: E501
                f"{exc.stderr.strip() if exc.stderr else 'unknown error'}"
            )
            raise RuntimeError(message) from exc
        except FileNotFoundError as exc:
            message = (
                f"Cannot register remote '{self.remote_name}': "
                f"Git is not installed or not found in PATH."
            )
            raise RuntimeError(message) from exc

    def unregister_as_remote(self) -> None:
        """Unregister this workspace's remote from the original repository.

        Removes the git remote named `arborinth/<workspace_name>` from the
        original repository.

        Silently ignores errors if the remote doesn't exist or git is
        unavailable.
        """
        try:
            subprocess.run(
                [
                    "git",
                    "remote",
                    "remove",
                    self.remote_name,
                ],
                cwd=self.project.repo_root_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # Ignore errors if the remote doesn't exist
            pass
        except FileNotFoundError:
            # Ignore if git is not available
            pass

    def delete(self) -> None:
        """Delete this workspace.

        Removes the workspace directory from the filesystem, including all its
        contents. Also removes the corresponding remote from the original
        repository if it exists.

        Raises:
            FileNotFoundError: If the workspace directory does not exist.
            OSError: If the directory cannot be removed.
        """
        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)

        self.unregister_as_remote()

        shutil.rmtree(self.root_path)

    def shell(
        self,
        args: typing.Sequence[str] | None = None,
        *,
        jail_backend: JailBackend = JailBackend.NONE,
        jail_config: JailConfig | None = None,
        project_root_path: pathlib.Path | None = None,
        home_path: pathlib.Path | None = None,
        additional_mounts: typing.Sequence[str] | None = None,
        hide_home: bool = True,
        expose_path_entries: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a shell or command in this workspace with the specified jail backend.

        This opens a shell session or runs a command in the workspace's workdir
        with the specified jail backend. If `args` is `None`, the jail's default
        behavior is used.

        The command is executed in the workspace's workdir directory, which
        contains the cloned Git repository. The process's stdout and stderr are
        not captured, allowing for interactive use.

        Args:
            args: The command and arguments to run. If `None`, runs the default
                shell.
            jail_backend: The jail backend to use.
            jail_config: A JailConfig object with all jail settings. If provided,
                this takes precedence over individual jail_* parameters.
            project_root_path: The project root path for .git access.
                Defaults to the workspace's project repo_root_path.
            home_path: The home directory to hide. Defaults to the current
                user's home directory.
            additional_mounts: Additional mount specifications (format: type:source[:dest]).
            hide_home: Whether to hide the home directory. Defaults to True.
            expose_path_entries: Whether to re-expose PATH entries from the
                hidden home directory. Defaults to True.

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.
        """
        # If jail_config is provided, use it (takes precedence)
        if jail_config is not None:
            # Apply defaults from workspace
            if jail_config.workdir_path is None or jail_config.workdir_path == pathlib.Path("."):
                jail_config = jail_config | JailConfig(workdir_path=self.workdir_path)
            if jail_config.project_root_path is None:
                jail_config = jail_config | JailConfig(project_root_path=self.project.repo_root_path)
            jail = jail_backend.value(**dataclasses.asdict(jail_config))
            return jail.run(args=args)

        # Legacy: use individual parameters (for backward compatibility)
        # Use project root from workspace if not specified
        if project_root_path is None:
            project_root_path = self.project.repo_root_path

        # Parse mount specifications
        mounts: list[MountSpec] = []
        if additional_mounts:
            for spec in additional_mounts:
                mounts.append(MountSpec.from_spec(spec))

        jail_class = jail_backend.value
        jail = jail_class(
            workdir_path=self.workdir_path,
            project_root_path=project_root_path,
            home_path=home_path,
            additional_mounts=mounts,
            hide_home=hide_home,
            expose_path_entries=expose_path_entries,
        )
        return jail.run(args=args)
