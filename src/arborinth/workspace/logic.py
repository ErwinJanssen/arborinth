"""Logic for the Arborinth's 'workspace' concept.

This module contains the core `Workspace` class which represents an isolated
workspace derived from a Git repository. Workspaces are clones of the original
repository where untrusted code can make changes without affecting the original
repository.
"""

from __future__ import annotations

import dataclasses
import shutil
import typing

if typing.TYPE_CHECKING:
    import pathlib

    from arborinth import Project


@dataclasses.dataclass
class Workspace:
    """An isolated workspace for untrusted code execution.

    A workspace is a clone of a Git repository where untrusted code can
    perform operations without affecting the original repository.

    Attributes:
        name: The name of the workspace.
        project: The Arborinth `Project` associated with the original repository.
    """

    name: str
    project: Project

    def __post_init__(self) -> None:
        """Validate the workspace after initialization.

        Raises:
            FileNotFoundError: If the workspace directory does not exist.
        """
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

    def delete(self) -> None:
        """Delete this workspace.

        Removes the workspace directory from the filesystem, including all
        its contents.

        Raises:
            FileNotFoundError: If the workspace directory does not exist.
            OSError: If the directory cannot be removed.
        """
        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)
        shutil.rmtree(self.root_path)
