"""Tests for the workspace CLI module."""

from __future__ import annotations

import typing

from arborinth.cli import main

if typing.TYPE_CHECKING:
    import pathlib

    import click.testing


class TestWorkspaceGroup:
    """Tests for the `workspace` command group."""

    def test_workspace_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `workspace` group."""
        result = cli_runner.invoke(main, ["workspace", "--help"])
        assert result.exit_code == 0
        assert "Manage Arborinth workspaces" in result.stdout
        assert "Usage:" in result.stdout

    def test_workspace_no_args(self, cli_runner: click.testing.CliRunner) -> None:
        """Workspace command group with no args should exit with non-zero exit code."""
        result = cli_runner.invoke(main, ["workspace"])
        assert result.exit_code != 0
        assert "Usage:" in result.stderr


class TestCreateCommand:
    """Tests for the `workspace create` command."""

    def test_create_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `create` command."""
        result = cli_runner.invoke(main, ["workspace", "create", "--help"])
        assert result.exit_code == 0
        assert "Create a new workspace" in result.stdout
        assert "NAME" in result.stdout

    def test_create_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command should create workspace directory."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["workspace", "create", "my_workspace"])
            assert result.exit_code == 0

            expected_path = tmp_git_repo / ".arborinth" / "workspaces" / "my_workspace"
            assert f"Created workspace: {expected_path}" in result.stdout
            assert expected_path.is_dir()

    def test_create_workspace_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Create command with explicit workdir should work."""
        result = cli_runner.invoke(
            main,
            ["--workdir", str(tmp_git_repo), "workspace", "create", "test_workspace"],
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
            main, ["-C", str(tmp_git_repo), "workspace", "create", "short_workspace"]
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
            result1 = cli_runner.invoke(main, ["workspace", "create", "duplicate"])
            assert result1.exit_code == 0

            # Second creation with same name should fail
            result2 = cli_runner.invoke(main, ["workspace", "create", "duplicate"])
            assert result2.exit_code != 0
            assert "Error:" in result2.output
            assert (
                "already exists" in result2.output.lower()
                or "file exists" in result2.output.lower()
            )


class TestDeleteCommand:
    """Tests for the `workspace delete` command."""

    def test_delete_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `delete` command."""
        result = cli_runner.invoke(main, ["workspace", "delete", "--help"])
        assert result.exit_code == 0
        assert "Delete a workspace" in result.stdout
        assert "NAME" in result.stdout

    def test_delete_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Delete command should remove the workspace directory."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            # Create a workspace first
            cli_runner.invoke(main, ["workspace", "create", "delete_test"])

            result = cli_runner.invoke(main, ["workspace", "delete", "delete_test"])
            assert result.exit_code == 0
            assert "Deleted workspace: delete_test" in result.stdout

            # Verify it's actually deleted
            expected_path = tmp_git_repo / ".arborinth" / "workspaces" / "delete_test"
            assert not expected_path.exists()

    def test_delete_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Delete command with explicit workdir should work."""
        # Create a workspace first
        cli_runner.invoke(
            main,
            ["--workdir", str(tmp_git_repo), "workspace", "create", "remote_delete"],
        )

        result = cli_runner.invoke(
            main,
            ["--workdir", str(tmp_git_repo), "workspace", "delete", "remote_delete"],
        )
        assert result.exit_code == 0
        assert "Deleted workspace: remote_delete" in result.stdout

    def test_delete_nonexistent_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Delete command with non-existent workspace should fail."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["workspace", "delete", "nonexistent"])
            assert result.exit_code != 0
            assert "Error:" in result.output
            assert "does not exist" in result.output


class TestInfoCommand:
    """Tests for the `workspace info` command."""

    def test_info_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `info` command."""
        result = cli_runner.invoke(main, ["workspace", "info", "--help"])
        assert result.exit_code == 0
        assert "Display information about a workspace" in result.stdout
        assert "NAME" in result.stdout

    def test_info_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info command should display workspace information."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            # Create a workspace first
            cli_runner.invoke(main, ["workspace", "create", "info_test"])

            result = cli_runner.invoke(main, ["workspace", "info", "info_test"])
            assert result.exit_code == 0
            assert "workspace name: info_test" in result.stdout
            assert "path:" in result.stdout
            assert ".arborinth/workspaces/info_test" in result.stdout
            assert "remote: arborinth/info_test" in result.stdout

    def test_info_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info command with explicit workdir should work."""
        # Create a workspace first
        cli_runner.invoke(
            main, ["--workdir", str(tmp_git_repo), "workspace", "create", "remote_info"]
        )

        result = cli_runner.invoke(
            main, ["--workdir", str(tmp_git_repo), "workspace", "info", "remote_info"]
        )
        assert result.exit_code == 0
        assert "workspace name: remote_info" in result.stdout
        assert "path:" in result.stdout

    def test_info_nonexistent_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """Info command with non-existent workspace should fail."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["workspace", "info", "nonexistent"])
            assert result.exit_code != 0
            assert "Error:" in result.output
            assert "does not exist" in result.output


class TestListCommand:
    """Tests for the `workspace list` command."""

    def test_list_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `list` command."""
        result = cli_runner.invoke(main, ["workspace", "list", "--help"])
        assert result.exit_code == 0
        assert "List workspaces for the project" in result.stdout

    def test_list_empty(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command with no workspaces should show empty message."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["workspace", "list"])
            assert result.exit_code != 0
            assert "No workspaces found" in result.stderr

    def test_list_workspaces(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command should list existing workspaces."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            # Create some workspaces first
            cli_runner.invoke(main, ["workspace", "create", "ws1"])
            cli_runner.invoke(main, ["workspace", "create", "ws2"])

            result = cli_runner.invoke(main, ["workspace", "list"])
            assert result.exit_code == 0
            assert "ws1" in result.stdout
            assert "ws2" in result.stdout

    def test_list_explicit_workdir(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """List command with explicit workdir should work."""
        # Create a workspace first
        cli_runner.invoke(
            main, ["--workdir", str(tmp_git_repo), "workspace", "create", "remote_ws"]
        )

        result = cli_runner.invoke(
            main, ["--workdir", str(tmp_git_repo), "workspace", "list"]
        )
        assert result.exit_code == 0
        assert "remote_ws" in result.stdout
