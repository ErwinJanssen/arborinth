"""Tests for the `project` logic module."""

import pathlib
import subprocess

import pytest

from arborinth.project import logic


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
