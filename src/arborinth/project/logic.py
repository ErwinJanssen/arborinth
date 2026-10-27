"""Logic for the Arborinth's 'project' concept.

This module contains the core `Project` class which represents a top-level
Arborinth project, typically associated with a Git repository.
"""

from __future__ import annotations

import dataclasses
import pathlib
import shutil
import subprocess

from arborinth import _util
from arborinth.workspace import Workspace


@dataclasses.dataclass
class Project:
    """A top-level Arborinth project associated with a Git repository.

    The `Project` class serves as a central entry point for Arborinth
    operations. It is designed to work closely with a Git repository, which is
    a central component of the Arborinth project concept. The project's working
    directory is expected to be within a Git repository.

    Attributes:
        workdir: The working directory path. Defaults to the current working
            directory. This should be within a Git repository.
        repo_root_path: Root path of the project's Git repository. Resolved
            once when the project is created, so that all paths derived from
            it are consistent.

    Raises:
        ValueError: If `workdir` is not an existing directory.
        RuntimeError: If `workdir` is not within a Git repository, or if Git
            is not installed.
    """

    workdir: pathlib.Path = dataclasses.field(default_factory=pathlib.Path.cwd)
    repo_root_path: pathlib.Path = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Validate the project attributes and resolve the repository root."""
        # Resolve `workdir` to an absolute path
        self.workdir = self.workdir.resolve()
        if not self.workdir.is_dir():
            message = (
                f"Project workdir must be an existing directory, got: {self.workdir}"
            )
            raise ValueError(message)

        # Resolve the Git repository root once, so that all paths derived
        # from it are consistent and no Git command is run per access.
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.workdir,
                capture_output=True,
                check=True,
                text=True,
            )
        except FileNotFoundError as exc:
            message = (
                f"Cannot determine Git root from {self.workdir}: "
                f"Git is not installed or not found in PATH."
            )
            raise RuntimeError(message) from exc
        except subprocess.CalledProcessError as exc:
            # git command failed - could be not in a repo or other git error
            # Check if the working directory itself has a .git directory or file
            # (worktrees have .git as a file pointing to the actual repo)
            git_path = self.workdir / ".git"
            if git_path.exists():
                # This might be a corrupted repo or worktree issue
                message = (
                    f"Cannot determine Git root from {self.workdir}: "
                    f"Git command failed but a .git entry exists. "
                    f"Is this a valid Git repository?"
                )
            else:
                stderr_msg = exc.stderr.strip() if exc.stderr else "unknown error"
                message = (
                    f"Cannot determine Git root from {self.workdir}: "
                    f"Git command failed: {stderr_msg}"
                )
            raise RuntimeError(message) from exc

        self.repo_root_path = pathlib.Path(result.stdout.strip())

    @property
    def workspace_root_path(self) -> pathlib.Path:
        """Root path for workspaces in this project.

        Returns:
            The absolute path to the `.arborinth/workspaces` directory.
        """
        return self.repo_root_path / ".arborinth" / "workspaces"

    @property
    def info(self) -> dict[str, str]:
        """Project information as a dictionary.

        Returns:
            A dictionary containing project root path and workspace root path.
        """
        return {
            "project_root": str(self.repo_root_path),
            "workspace_root": str(self.workspace_root_path),
        }

    def create_workspace(self, name: str) -> Workspace:
        """Create a new workspace.

        Creates a workspace with the given name in the project's workspace
        directory. The workspace is initialized by cloning the project's Git
        repository into the workspace's `workdir` subdirectory. The clone uses
        an isolated Git configuration to prevent the host system's Git config
        from affecting the operation. The clone's `origin` remote is set to a
        relative path, so that the workspace keeps working when the repository
        directory is moved.

        Also adds the workspace's clone as a remote in the original repository
        with the name `arborinth/<workspace_name>`, allowing the original repo
        to pull changes from the workspace. Like the clone's `origin`, the
        remote uses a relative path.

        Args:
            name: The name of the workspace to create.

        Returns:
            A `Workspace` instance for the created workspace.

        Raises:
            ValueError: If the workspace name is invalid.
            FileExistsError: If a workspace with this name already exists.
            RuntimeError: If Git is not installed, if the Git repository
                cannot be cloned, or if adding the remote fails.
        """
        _util.validate_workspace_name(name)

        # Git must be available for the clone. Check before any directories
        # are created, so that a missing Git installation is not confused with
        # other `FileNotFoundError`s raised by the clone, and so that no
        # directories are left behind.
        if shutil.which("git") is None:
            message = (
                f"Cannot clone repository for workspace '{name}': "
                f"Git is not installed or not found in PATH."
            )
            raise RuntimeError(message)

        workspace_path = self.workspace_root_path / name

        # Check if workspace already exists
        if workspace_path.exists():
            message = f"Workspace '{name}' already exists at {workspace_path}"
            raise FileExistsError(message)

        # Ensure the project workspace root directory exists
        self.workspace_root_path.mkdir(parents=True, exist_ok=True)

        # Create the workspace directory structure
        workspace_path.mkdir()
        workdir_path = workspace_path / "workdir"

        # Clone the repository into the workspace/workdir directory. Do not use
        # the host system's Git configuration for improved isolation and
        # reproducibility. Also disable terminal prompts to prevent interactive
        # behavior.
        env = {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }

        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    # Use `--no-local` to prevent hardlinks (ensures full copy
                    # for isolation)
                    "--no-local",
                    str(self.repo_root_path),
                    str(workdir_path),
                ],
                cwd=self.workdir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            # Clean up the directory if clone failed
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            message = (
                f"Failed to clone repository into workspace '{name}': "
                f"{exc.stderr.strip() if exc.stderr else 'unknown error'}"
            )
            raise RuntimeError(message) from exc
        except FileNotFoundError as exc:
            # Clean up the directory if the clone failed. Git availability is
            # checked upfront, so the error has another cause, such as a
            # missing working directory.
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            message = f"Cannot clone repository for workspace '{name}': {exc}"
            raise RuntimeError(message) from exc

        # Create the Workspace instance (directory exists, validation passes)
        workspace = Workspace(name=name, project=self)

        # Point the clone's origin remote at the original repository with a
        # relative path, and register the workspace as a remote in the
        # original repository.
        try:
            workspace.set_relative_origin_url()
            workspace.register_as_remote()
        except RuntimeError:
            # Clean up the workspace directory if either step failed
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise

        return workspace

    @property
    def workspaces(self) -> list[Workspace]:
        """List of workspaces for this project.

        Returns:
            A list of Workspace objects that exist for the project.
        """
        try:
            return [
                Workspace(name=entry.name, project=self)
                for entry in self.workspace_root_path.iterdir()
                if entry.is_dir()
            ]
        except FileNotFoundError:
            return []

    def workspace(self, name: str) -> Workspace:
        """Retrieve a workspace by name.

        Args:
            name: The name of the workspace to retrieve.

        Returns:
            A `Workspace` instance for the specified workspace.

        Raises:
            FileNotFoundError: If no workspace with this name exists.
        """
        return Workspace(name=name, project=self)
