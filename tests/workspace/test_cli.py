"""Tests for the workspace CLI module."""

from __future__ import annotations

import typing

from arborinth.workspace import cli

if typing.TYPE_CHECKING:
    import pathlib

    import click.testing


class TestWorkspaceGroup:
    """Tests for the `workspace` command group."""

    def test_workspace_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `workspace` group."""
        result = cli_runner.invoke(cli.workspace, ["--help"])
        assert result.exit_code == 0
        assert "Manage Arborinth workspaces" in result.stdout
        assert "Usage:" in result.stdout

    def test_workspace_no_args(self, cli_runner: click.testing.CliRunner) -> None:
        """Workspace command group with no args should exit with non-zero exit code."""
        result = cli_runner.invoke(cli.workspace, [])
        assert result.exit_code != 0
        assert "Usage:" in result.stderr


class TestCreateCommand:
    """Tests for the `workspace create` command."""

    def test_create_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `create` command."""
        result = cli_runner.invoke(cli.create, ["--help"])
        assert result.exit_code == 0
        assert "Create a new workspace" in result.stdout
        assert "NAME" in result.stdout

    def test_create_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command should create workspace directory."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(cli.create, ["my_workspace"])
            assert result.exit_code == 0

            expected_path = tmp_git_repo / ".arborinth" / "workspaces" / "my_workspace"
            assert f"Created workspace: {expected_path}" in result.stdout
            assert expected_path.is_dir()

    def test_create_workspace_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command with explicit workdir should work."""
        result = cli_runner.invoke(
            cli.create, ["--workdir", str(tmp_git_repo), "test_workspace"]
        )
        assert result.exit_code == 0

        expected_path = tmp_git_repo / ".arborinth" / "workspaces" / "test_workspace"
        assert f"Created workspace: {expected_path}" in result.stdout
        assert expected_path.is_dir()

    def test_create_workspace_short_workdir_flag(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command with -C flag should work."""
        result = cli_runner.invoke(
            cli.create, ["-C", str(tmp_git_repo), "short_workspace"]
        )
        assert result.exit_code == 0

        expected_path = tmp_git_repo / ".arborinth" / "workspaces" / "short_workspace"
        assert f"Created workspace: {expected_path}" in result.stdout
        assert expected_path.is_dir()

    def test_create_duplicate_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command with duplicate name should fail."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            # First creation should succeed
            result1 = cli_runner.invoke(cli.create, ["duplicate"])
            assert result1.exit_code == 0

            # Second creation with same name should fail
            result2 = cli_runner.invoke(cli.create, ["duplicate"])
            assert result2.exit_code != 0
            assert "Error:" in result2.output
            assert (
                "already exists" in result2.output.lower()
                or "file exists" in result2.output.lower()
            )

    def test_create_nonexistent_workdir(
        self, cli_runner: click.testing.CliRunner
    ) -> None:
        """Create command with non-existent workdir should fail."""
        result = cli_runner.invoke(
            cli.create, ["--workdir", "/nonexistent/path/12345", "some_workspace"]
        )
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "must be an existing directory" in result.output

    def test_create_outside_git_repo(
        self, cli_runner: click.testing.CliRunner, tmp_path: pathlib.Path
    ) -> None:
        """Create command from outside git repo should fail."""
        result = cli_runner.invoke(
            cli.create, ["--workdir", str(tmp_path), "workspace"]
        )
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "Cannot determine Git root" in result.output


class TestListCommand:
    """Tests for the `workspace list` command."""

    def test_list_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `list` command."""
        result = cli_runner.invoke(cli.list_, ["--help"])
        assert result.exit_code == 0
        assert "List workspaces for the project" in result.stdout

    def test_list_empty(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command with no workspaces should show empty message."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(cli.list_, [])
            assert result.exit_code != 0
            assert "No workspaces found" in result.stderr

    def test_list_workspaces(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command should list existing workspaces."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            # Create some workspaces first
            cli_runner.invoke(cli.create, ["ws1"])
            cli_runner.invoke(cli.create, ["ws2"])

            result = cli_runner.invoke(cli.list_, [])
            assert result.exit_code == 0
            assert "ws1" in result.stdout
            assert "ws2" in result.stdout

    def test_list_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command with explicit workdir should work."""
        # Create a workspace first
        cli_runner.invoke(cli.create, ["--workdir", str(tmp_git_repo), "remote_ws"])

        result = cli_runner.invoke(cli.list_, ["--workdir", str(tmp_git_repo)])
        assert result.exit_code == 0
        assert "remote_ws" in result.stdout

    def test_list_nonexistent_workdir(
        self, cli_runner: click.testing.CliRunner
    ) -> None:
        """List command with non-existent workdir should fail."""
        result = cli_runner.invoke(cli.list_, ["--workdir", "/nonexistent/path/12345"])
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "must be an existing directory" in result.output

    def test_list_outside_git_repo(
        self, cli_runner: click.testing.CliRunner, tmp_path: pathlib.Path
    ) -> None:
        """List command from outside git repo should fail."""
        result = cli_runner.invoke(cli.list_, ["--workdir", str(tmp_path)])
        assert result.exit_code != 0
        assert "Error:" in result.output
        assert "Cannot determine Git root" in result.output
