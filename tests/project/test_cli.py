"""Tests for the Project CLI module."""

from __future__ import annotations

import typing

from arborinth.project import cli

if typing.TYPE_CHECKING:
    import pathlib

    import click.testing


class TestProjectGroup:
    """Tests for the `project` command group."""

    def test_project_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `project` group."""
        result = cli_runner.invoke(cli.project, ["--help"])
        assert result.exit_code == 0
        assert "Manage an Arborinth project" in result.stdout
        assert "Usage:" in result.stdout

    def test_project_no_args(self, cli_runner: click.testing.CliRunner) -> None:
        """Project command group with no args should exit with non-zero exit code."""
        result = cli_runner.invoke(cli.project, [])
        assert result.exit_code != 0
        assert "Usage:" in result.stderr


class TestInfoCommand:
    """Tests for the `project info` command."""

    def test_info_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `info` command."""
        result = cli_runner.invoke(cli.info, ["--help"])
        assert result.exit_code == 0
        assert "Display information about the current project" in result.stdout
        assert "workspace root path" in result.stdout
        assert "--workdir" in result.stdout

    def test_info_default_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with default workdir should show project and workspace roots."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(cli.info, [])
            assert result.exit_code == 0

            expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
            assert f"Project root: {tmp_git_repo}" in result.stdout
            assert f"Workspace root: {expected_workspace_root}" in result.stdout

    def test_info_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with explicit workdir should show project and workspace roots."""
        result = cli_runner.invoke(cli.info, ["--workdir", str(tmp_git_repo)])
        assert result.exit_code == 0

        expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
        assert f"Project root: {tmp_git_repo}" in result.stdout
        assert f"Workspace root: {expected_workspace_root}" in result.stdout

    def test_info_short_workdir_flag(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info with -C flag should work."""
        result = cli_runner.invoke(cli.info, ["-C", str(tmp_git_repo)])
        assert result.exit_code == 0

        expected_workspace_root = tmp_git_repo / ".arborinth" / "workspaces"
        assert f"Project root: {tmp_git_repo}" in result.stdout
        assert f"Workspace root: {expected_workspace_root}" in result.stdout

    def test_info_nonexistent_workdir(
        self, cli_runner: click.testing.CliRunner
    ) -> None:
        """Info with non-existent workdir should fail gracefully."""
        result = cli_runner.invoke(cli.info, ["--workdir", "/nonexistent/path/12345"])
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "must be an existing directory" in result.output

    def test_info_outside_git_repo(
        self, cli_runner: click.testing.CliRunner, tmp_path: pathlib.Path
    ) -> None:
        """Info from outside git repo should fail gracefully."""
        result = cli_runner.invoke(cli.info, ["--workdir", str(tmp_path)])
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "Cannot determine Git root" in result.output
