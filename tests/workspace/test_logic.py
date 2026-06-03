"""Tests for the `workspace` logic module."""

from __future__ import annotations

import shutil
import typing

import pytest

from arborinth.workspace import logic
from tests import INVALID_WORKSPACE_NAME_INPUTS

if typing.TYPE_CHECKING:
    from arborinth import Project


class TestWorkspaceInit:
    """Tests for `Workspace` initialization and validation."""

    def test_valid_name(self, tmp_project: Project) -> None:
        """`Workspace` with valid name should initialize successfully."""
        workspace = tmp_project.create_workspace("test")
        assert workspace.name == "test"
        assert workspace.project == tmp_project

    def test_nonexistent_workspace_raises(self, tmp_project: Project) -> None:
        """`Workspace` with non-existent name should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="does not exist"):
            logic.Workspace(name="nonexistent", project=tmp_project)

    @pytest.mark.parametrize(**INVALID_WORKSPACE_NAME_INPUTS)
    def test_invalid_name_raises(
        self,
        tmp_project: Project,
        name: str,
        exception_type: type[Exception],
        message_substring: str,
    ) -> None:
        """`Workspace` with invalid name should raise ValueError."""
        with pytest.raises(exception_type, match=message_substring):
            logic.Workspace(name=name, project=tmp_project)


class TestWorkspacePaths:
    """Tests for workspace path properties."""

    def test_root_path(self, tmp_project: Project) -> None:
        """`root_path` should return correct path."""
        tmp_project.create_workspace("test")
        workspace = tmp_project.workspace("test")
        expected = tmp_project.workspace_root_path / "test"
        assert workspace.root_path == expected

    def test_workdir_path(self, tmp_project: Project) -> None:
        """workdir_path should return correct path to workdir subdirectory."""
        tmp_project.create_workspace("test")
        workspace = tmp_project.workspace("test")

        expected = tmp_project.workspace_root_path / "test" / "workdir"
        assert workspace.workdir_path == expected


class TestWorkspaceDelete:
    """Tests for the `delete` method."""

    def test_delete_workspace(self, tmp_project: Project) -> None:
        """`delete` should remove the workspace directory."""
        workspace = tmp_project.create_workspace("to_delete")
        assert workspace.root_path.is_dir()

        workspace.delete()
        assert not workspace.root_path.exists()

    def test_delete_nonexistent_workspace(self, tmp_project: Project) -> None:
        """`delete` should raise FileNotFoundError for non-existent workspace."""
        workspace = tmp_project.create_workspace("to_delete")

        # Remove the workspace directory to simulate non-existence
        shutil.rmtree(workspace.root_path)

        with pytest.raises(FileNotFoundError, match="does not exist"):
            workspace.delete()
