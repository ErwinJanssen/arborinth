"""Tests for the shell CLI module."""

from __future__ import annotations

import typing

from arborinth.cli import main

if typing.TYPE_CHECKING:
    import pathlib

    import click.testing

    from arborinth import Workspace


class TestShellCommand:
    """Tests for the `shell` command."""

    def test_shell_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `shell` command."""
        result = cli_runner.invoke(main, ["shell", "--help"])
        assert result.exit_code == 0
        assert "Run a shell or command in a workspace" in result.stdout
        assert "Usage:" in result.stdout

    def test_shell_default_jail_backend(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`shell` command should default to NONE jail backend."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            # Verify the default is NONE by checking the help output
            result = cli_runner.invoke(main, ["shell", "--help"])
            assert "[default: none]" in result.stdout

            # Verify it works with the default
            result = cli_runner.invoke(
                main,
                ["shell", tmp_workspace.name, "echo", "test"],
            )
            assert result.exit_code == 0

    def test_shell_requires_workspace_name(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """`shell` command should require a workspace name argument."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["shell"])
            assert result.exit_code != 0

    def test_shell_with_nonexistent_workspace(
        self, cli_runner: click.testing.CliRunner, tmp_git_repo: pathlib.Path
    ) -> None:
        """`shell` with non-existent workspace should raise error."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_git_repo):
            result = cli_runner.invoke(main, ["shell", "nonexistent_workspace"])
            assert result.exit_code != 0
            assert "does not exist" in result.output

    def test_shell_with_command(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`shell` with workspace and command should execute the command."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                ["shell", tmp_workspace.name, "echo", "hello"],
            )
            assert result.exit_code == 0

    def test_shell_propates_exit_code(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`shell` should propagate the exit code of the command."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                ["shell", tmp_workspace.name, "false"],
            )
            assert result.exit_code == 1

    def test_shell_with_workspace_only(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`shell` with only workspace name should start default shell."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            # When only workspace name is provided, it should start a shell. It
            # tricky to test if the shell is actually started, but it should not
            # fail complaining about missing command, since that is optional.
            result = cli_runner.invoke(
                main,
                ["shell", tmp_workspace.name],
            )
            assert result.exit_code == 0
