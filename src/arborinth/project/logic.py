"""Logic for the Arborinth's 'project' concept.

This module contains the core `Project` class which represents a top-level
Arborinth project, typically associated with a Git repository.
"""

from __future__ import annotations

import dataclasses
import pathlib
import subprocess

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

    Raises:
        ValueError: If `workdir` is not an existing directory.
    """

    workdir: pathlib.Path = dataclasses.field(default_factory=pathlib.Path.cwd)

    def __post_init__(self) -> None:
        """Validate the project attributes after initialization."""
        # Resolve `workdir` to an absolute path
        self.workdir = self.workdir.resolve()
        if not self.workdir.is_dir():
            message = (
                f"Project workdir must be an existing directory, got: {self.workdir}"
            )
            raise ValueError(message)

    @property
    def repo_root_path(self) -> pathlib.Path:
        """Root path of the Git repository for this project.

        Uses the current working directory to determine the Git root by running
        `git rev-parse --show-toplevel`.

        Returns:
            The absolute path to the Git repository root.

        Raises:
            RuntimeError: If `workdir` is not within a Git repository, or if
                Git is not installed.
        """
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

        return pathlib.Path(result.stdout.strip())

    @property
    def workspace_root_path(self) -> pathlib.Path:
        """Root path for workspaces in this project.

        Returns:
            The absolute path to the `.arborinth/workspaces` directory.
        """
        return self.repo_root_path / ".arborinth" / "workspaces"

    def create_workspace(self, name: str) -> Workspace:
        """Create a new workspace.

        Creates a workspace with the given name in the workspace root directory.

        Args:
            name: The name of the workspace to create.

        Returns:
            A `Workspace` instance for the created workspace.

        Raises:
            FileExistsError: If a workspace with this name already exists.
        """
        workspace_path = self.workspace_root_path / name
        workspace_path.mkdir(parents=True, exist_ok=False)
        return Workspace(name=name, project=self)
