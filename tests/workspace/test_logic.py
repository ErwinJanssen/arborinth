"""Tests for the `workspace` logic module."""

from __future__ import annotations

import typing

from arborinth.workspace import logic

if typing.TYPE_CHECKING:
    from arborinth import Project


class TestWorkspaceInit:
    """Tests for `Workspace` initialization and validation."""

    def test_valid_name(self, tmp_project: Project) -> None:
        """`Workspace` with valid name should initialize successfully."""
        workspace = logic.Workspace(name="test", project=tmp_project)
        assert workspace.name == "test"
        assert workspace.project == tmp_project


class TestWorkspacePaths:
    """Tests for workspace path properties."""

    def test_root_path(self, tmp_project: Project) -> None:
        """`root_path` should return correct path."""
        workspace = logic.Workspace(name="test", project=tmp_project)
        expected = tmp_project.workspace_root_path / "test"
        assert workspace.root_path == expected
