"""Tests for the `workspace` logic module."""

from __future__ import annotations

import os
import shutil
import subprocess
import typing

import pytest

from arborinth.workspace import logic
from tests import INVALID_WORKSPACE_NAME_INPUTS, generate_random_string

if typing.TYPE_CHECKING:
    from arborinth import Project, Workspace


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


class TestInfo:
    """Tests for the `info` property."""

    def test_info_returns_dict(self, tmp_project: Project) -> None:
        """`info` should return a dictionary."""
        workspace = tmp_project.create_workspace("test")
        info = workspace.info
        assert isinstance(info, dict)

    def test_info_contains_workspace_name(self, tmp_project: Project) -> None:
        """`info` should contain workspace name."""
        workspace = tmp_project.create_workspace("test_name")
        info = workspace.info
        assert "workspace_name" in info
        assert info["workspace_name"] == "test_name"

    def test_info_contains_path(self, tmp_project: Project) -> None:
        """`info` should contain workspace path."""
        workspace = tmp_project.create_workspace("test")
        info = workspace.info
        assert "path" in info
        assert info["path"] == str(workspace.root_path)

    def test_info_contains_remote(self, tmp_project: Project) -> None:
        """`info` should contain remote name."""
        workspace = tmp_project.create_workspace("test")
        info = workspace.info
        assert "remote" in info
        assert info["remote"] == f"arborinth/{workspace.name}"


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

    def test_delete_workspace_removes_remote(self, tmp_project: Project) -> None:
        """`delete` should remove the corresponding remote from original repo."""
        workspace = tmp_project.create_workspace("test_remote_remove")

        # Verify the remote was added during creation
        remote_name = f"arborinth/{workspace.name}"
        proc = subprocess.run(
            ["git", "remote", "-v"],
            cwd=tmp_project.repo_root_path,
            capture_output=True,
            check=True,
            text=True,
        )
        assert remote_name in proc.stdout

        # Delete the workspace
        workspace.delete()

        # Verify the remote was removed
        proc = subprocess.run(
            ["git", "remote", "-v"],
            cwd=tmp_project.repo_root_path,
            capture_output=True,
            check=True,
            text=True,
        )
        assert remote_name not in proc.stdout


class TestWorkspaceShell:
    """Tests for the `shell` method."""

    def test_shell_with_command(self, tmp_workspace: Workspace) -> None:
        """`shell` should execute a command in the workspace workdir."""
        # Run a simple command that should succeed
        args = ["git", "status"]
        proc = tmp_workspace.shell(args=args)

        assert isinstance(proc, subprocess.CompletedProcess)
        assert proc.args == args
        assert proc.returncode == 0

    def test_shell_with_no_args_uses_default_shell(
        self, tmp_workspace: Workspace
    ) -> None:
        """`shell` with no args should use default shell."""
        # Get default shell from env, with fallbacks matching the implementation
        shell = os.environ.get("SHELL")
        if not shell or shutil.which(shell) is None:
            shell = shutil.which("bash") or shutil.which("sh")

        # When no args are provided, it should use the default shell
        proc = tmp_workspace.shell(args=None)
        assert proc.args == [shell]

    def test_shell_runs_in_workdir(self, tmp_workspace: Workspace) -> None:
        """`shell` should run command in the workspace's workdir."""
        # Verify that `shell` method uses correct `cwd` by creating a file and
        # checking it exists in the workdir.
        reference_file = generate_random_string()

        proc = tmp_workspace.shell(args=["touch", reference_file])
        assert proc.returncode == 0
        assert (tmp_workspace.workdir_path / reference_file).exists()

    def test_shell_with_invalid_command_raises(self, tmp_workspace: Workspace) -> None:
        """`shell` with invalid command should raise `FileNotFoundError`."""
        with pytest.raises(FileNotFoundError, match="No such file"):
            tmp_workspace.shell(args=["nonexistent_command_xyz"])
