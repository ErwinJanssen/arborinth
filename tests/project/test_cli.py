"""Tests for the Project CLI module."""

from __future__ import annotations

import typing

from arborinth.cli import main

if typing.TYPE_CHECKING:
    import pathlib

    import click.testing


class TestProjectGroup:
    """Tests for the `project` command group."""

    def test_project_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `project` group."""
        result = cli_runner.invoke(main, ["project", "--help"])
        assert result.exit_code == 0
        assert "Manage an Arborinth project" in result.stdout
        assert "Usage:" in result.stdout

    def test_project_no_args(self, cli_runner: click.testing.CliRunner) -> None:
        """Project command group with no args should exit with non-zero exit code."""
        result = cli_runner.invoke(main, ["project"])
        assert result.exit_code != 0
        assert "Usage:" in result.stderr


class TestInfoCommand:
    """Tests for the `project info` command."""

    def test_info_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `info` command."""
        result = cli_runner.invoke(main, ["project", "info", "--help"])
        assert result.exit_code == 0
        assert "Display information about the current project" in result.stdout
        assert "workspace root path" in result.stdout

    def test_info_default_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with default workdir should show project and workspace roots."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["project", "info"])
            assert result.exit_code == 0

            expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
            assert f"project root: {tmp_git_repo}" in result.stdout
            assert f"workspace root: {expected_workspace_root}" in result.stdout

    def test_info_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with explicit workdir should show project and workspace roots."""
        result = cli_runner.invoke(
            main, ["--workdir", str(tmp_git_repo), "project", "info"]
        )
        assert result.exit_code == 0

        expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
        assert f"project root: {tmp_git_repo}" in result.stdout
        assert f"workspace root: {expected_workspace_root}" in result.stdout

    def test_info_short_workdir_flag(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with -C flag should work."""
        result = cli_runner.invoke(main, ["-C", str(tmp_git_repo), "project", "info"])
        assert result.exit_code == 0

        expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
        assert f"project root: {tmp_git_repo}" in result.stdout
        assert f"workspace root: {expected_workspace_root}" in result.stdout

    def test_info_outside_git_repo_fails(
        self, cli_runner: click.testing.CliRunner, tmp_path: pathlib.Path
    ) -> None:
        """Info command should fail when not in a git repository."""
        result = cli_runner.invoke(main, ["--workdir", str(tmp_path), "project", "info"])
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "Git" in result.output or "git" in result.output
