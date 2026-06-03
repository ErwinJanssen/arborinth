"""Tests for the `workspace` logic module."""

from __future__ import annotations

import typing

import pytest

from arborinth.workspace import logic

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


class TestWorkspacePaths:
    """Tests for workspace path properties."""

    def test_root_path(self, tmp_project: Project) -> None:
        """`root_path` should return correct path."""
        tmp_project.create_workspace("test")
        workspace = tmp_project.workspace("test")
        expected = tmp_project.workspace_root_path / "test"
        assert workspace.root_path == expected
