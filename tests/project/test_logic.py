"""Tests for the `project` logic module."""

import pathlib
import subprocess

import pytest

from arborinth import Workspace
from arborinth.project import logic
from tests import INVALID_WORKSPACE_NAME_INPUTS


class TestProjectInit:
    """Tests for `Project` initialization and validation."""

    def test_default_workdir(self) -> None:
        """`Project` with default workdir should use current working directory."""
        project = logic.Project()
        assert project.workdir == pathlib.Path.cwd()

    def test_explicit_workdir(self, tmp_path: pathlib.Path) -> None:
        """`Project` with explicit workdir should use that path."""
        project = logic.Project(workdir=tmp_path)
        assert project.workdir == tmp_path

    def test_nonexistent_workdir_raises(self) -> None:
        """`Project` with non-existent workdir should raise `ValueError`."""
        with pytest.raises(ValueError, match="must be an existing directory"):
            logic.Project(workdir=pathlib.Path("/nonexistent/path/12345"))

    def test_file_path_raises(self, tmp_path: pathlib.Path) -> None:
        """`Project` with file path (not directory) should raise `ValueError`."""
        # Create a temporary file
        temp_file = tmp_path / "test_file"
        temp_file.touch()
        with pytest.raises(ValueError, match="must be an existing directory"):
            logic.Project(workdir=temp_file)


class TestRepoRootPath:
    """Tests for the `repo_root_path` property."""

    def test_repo_root_in_git_repo(self, tmp_git_repo: pathlib.Path) -> None:
        """repo_root_path should return correct git root when in a repo."""
        project = logic.Project(workdir=tmp_git_repo)
        root = project.repo_root_path

        # Verify it's a `pathlib.Path`
        assert isinstance(root, pathlib.Path)

        # Verify it looks like a git root (has `.git`)
        assert (root / ".git").is_dir()

    def test_repo_root_from_subdirectory(self, tmp_git_repo: pathlib.Path) -> None:
        """repo_root_path should find root from subdirectory."""
        # Create a subdirectory within the git repo
        subdir = tmp_git_repo / "subdir"
        subdir.mkdir()

        project = logic.Project(workdir=subdir)
        root = project.repo_root_path

        assert isinstance(root, pathlib.Path)
        assert (root / ".git").is_dir()

        # The root should be the git repo root
        assert root == tmp_git_repo

    def test_repo_root_outside_git_repo_raises(self, tmp_path: pathlib.Path) -> None:
        """repo_root_path should raise RuntimeError when not in a git repo."""
        project = logic.Project(workdir=tmp_path)

        with pytest.raises(
            RuntimeError, match=r"Cannot determine Git root.*Git command failed"
        ):
            _ = project.repo_root_path

    def test_repo_root_with_mocked_git_failure(self, tmp_path: pathlib.Path) -> None:
        """repo_root_path should raise RuntimeError when git command fails."""
        # Create a directory with a .git file (simulating a corrupted repo)
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / ".git").touch()

        project = logic.Project(workdir=test_dir)

        with pytest.raises(
            RuntimeError, match=r"Git command failed.*a \.git entry exists"
        ):
            _ = project.repo_root_path

    def test_repo_root_git_not_installed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """repo_root_path should raise RuntimeError when git is not installed."""

        # Mock subprocess.run to raise FileNotFoundError (git not found)
        def mock_run(*_args: object, **_kwargs: object) -> None:
            message = "git not found"
            raise FileNotFoundError(message)

        monkeypatch.setattr(subprocess, "run", mock_run)

        project = logic.Project(workdir=tmp_path)

        with pytest.raises(
            RuntimeError, match=r"Cannot determine Git root.*Git is not installed"
        ):
            _ = project.repo_root_path


class TestWorkspaceRootPath:
    """Tests for the `workspace_root_path` property."""

    def test_workspace_root_path(self, tmp_project: logic.Project) -> None:
        """`workspace_root_path` should return correct path."""
        expected = tmp_project.repo_root_path / ".arborinth" / "workspaces"
        assert tmp_project.workspace_root_path == expected


class TestCreateWorkspace:
    """Tests for the `create_workspace` method."""

    def test_create_workspace(self, tmp_project: logic.Project) -> None:
        """`create_workspace` should create a Workspace instance."""
        workspace = tmp_project.create_workspace("test_workspace")

        assert isinstance(workspace, Workspace)
        assert workspace.name == "test_workspace"
        assert workspace.project == tmp_project
        assert workspace.root_path == tmp_project.workspace_root_path / "test_workspace"
        assert workspace.root_path.is_dir()

    def test_create_workspace_duplicate_raises(
        self, tmp_project: logic.Project
    ) -> None:
        """`create_workspace` should raise `FileExistsError` for duplicate name."""
        tmp_project.create_workspace("duplicate")

        with pytest.raises(FileExistsError):
            tmp_project.create_workspace("duplicate")

    @pytest.mark.parametrize(**INVALID_WORKSPACE_NAME_INPUTS)
    def test_invalid_name_raises(
        self,
        tmp_project: logic.Project,
        name: str,
        exception_type: type[Exception],
        message_substring: str,
    ) -> None:
        """`Workspace` with invalid name should raise ValueError."""
        with pytest.raises(exception_type, match=message_substring):
            tmp_project.create_workspace(name)

    def test_create_workspace_creates_git_repo(
        self, tmp_project: logic.Project
    ) -> None:
        """`create_workspace` should create a valid Git repository in workdir."""
        workspace = tmp_project.create_workspace("test_git_workspace")

        # Check that the `workspace.workdir_path` directory contains a .git
        # directory
        assert workspace.workdir_path.is_dir()
        assert (workspace.workdir_path / ".git").is_dir()

        # Check that git commands work in the workspace.workdir_path directory
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=workspace.workdir_path,
            capture_output=True,
            check=True,
            text=True,
        )
        assert proc.stdout.strip() == str(workspace.workdir_path)

    def test_create_workspace_adds_remote_to_original_repo(
        self, tmp_project: logic.Project
    ) -> None:
        """`create_workspace` should add workspace clone as remote in original repo."""
        workspace = tmp_project.create_workspace("test_remote_workspace")

        # Check that the remote was added to the original repository
        remote_name = f"arborinth/{workspace.name}"
        proc = subprocess.run(
            ["git", "remote", "-v"],
            cwd=tmp_project.repo_root_path,
            capture_output=True,
            check=True,
            text=True,
        )

        # Check that the remote exists in the output
        assert remote_name in proc.stdout
        assert str(workspace.workdir_path) in proc.stdout

    def test_create_workspace_git_not_installed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_project: logic.Project
    ) -> None:
        """`create_workspace` should raise RuntimeError when git is not installed."""

        def mock_run(*_args: object, **_kwargs: object) -> None:
            message = "git not found"
            raise FileNotFoundError(message)

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Git is not installed"):
            tmp_project.create_workspace("test_no_git")

    def test_create_workspace_clone_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_project: logic.Project
    ) -> None:
        """`create_workspace` should raise RuntimeError when git clone fails."""
        original_run = subprocess.run

        def mock_run(cmd: list[str], *args: object, **kwargs: object) -> None:
            # Only mock the git clone command, let other git commands pass through
            if cmd and cmd[0] == "git" and len(cmd) > 1 and cmd[1] == "clone":
                exc = subprocess.CalledProcessError(
                    128, cmd, stderr="repository not found"
                )
                raise exc
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Failed to clone repository"):
            tmp_project.create_workspace("test_clone_fail")


class TestWorkspace:
    """Tests for the `workspace` method."""

    def test_workspace_retrieves_existing(self, tmp_project: logic.Project) -> None:
        """`workspace` should retrieve an existing workspace."""
        created_workspace = tmp_project.create_workspace("test_workspace")
        retrieved_workspace = tmp_project.workspace(created_workspace.name)

        assert retrieved_workspace == created_workspace

    def test_workspace_nonexistent_raises(self, tmp_project: logic.Project) -> None:
        """`workspace` should raise FileNotFoundError for non-existent workspace."""
        with pytest.raises(FileNotFoundError, match="does not exist"):
            tmp_project.workspace("nonexistent")


class TestWorkspaces:
    """Tests for the `workspaces` property."""

    def test_workspaces_empty(self, tmp_project: logic.Project) -> None:
        """Workspaces should return empty list when no workspaces exist."""
        assert tmp_project.workspaces == []

    def test_workspaces_returns_workspace_objects(
        self, tmp_project: logic.Project
    ) -> None:
        """Workspaces should return list of Workspace objects."""
        workspace_names = {"workspace1", "workspace2"}
        for name in workspace_names:
            tmp_project.create_workspace(name)

        workspaces = tmp_project.workspaces
        assert len(workspaces) == len(workspace_names)
        assert all(isinstance(ws, logic.Workspace) for ws in workspaces)
        assert {ws.name for ws in workspaces} == workspace_names
