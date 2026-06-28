"""Tests for the shell CLI module."""

from __future__ import annotations

import typing
from unittest.mock import patch

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

    def test_shell_mount_option_in_help(
        self, cli_runner: click.testing.CliRunner
    ) -> None:
        """`--help` should show --mount option."""
        result = cli_runner.invoke(main, ["shell", "--help"])
        assert result.exit_code == 0
        assert "--mount" in result.stdout

    def test_shell_with_valid_mount(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--mount` with a valid mount spec should work."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--mount",
                    "ro:/nonexistent",
                    "echo",
                    "test",
                ],
            )
            assert result.exit_code == 0

    def test_shell_with_multiple_mounts(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """Multiple `--mount` options should all be accepted."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--mount",
                    "ro:/src1:/dest1",
                    "--mount",
                    "tmpfs:/tmp",
                    "echo",
                    "test",
                ],
            )
            assert result.exit_code == 0

    def test_shell_with_invalid_mount(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--mount` with invalid spec should show clear error."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                ["shell", tmp_workspace.name, "--mount", "invalid", "echo", "test"],
            )
            assert result.exit_code != 0
            assert "Invalid mount spec" in result.output

    def test_shell_preset_option_in_help(
        self, cli_runner: click.testing.CliRunner
    ) -> None:
        """`--help` should show --preset option."""
        result = cli_runner.invoke(main, ["shell", "--help"])
        assert result.exit_code == 0
        assert "--preset" in result.stdout

    def test_shell_with_valid_preset(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--preset` with a valid preset name should work."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--preset",
                    "opencode",
                    "echo",
                    "test",
                ],
            )
            assert result.exit_code == 0

    def test_shell_with_invalid_preset(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--preset` with unknown name should show clear error."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--preset",
                    "nonexistent",
                    "echo",
                    "test",
                ],
            )
            assert result.exit_code != 0
            assert "Unknown preset" in result.output

    def test_shell_with_multiple_presets(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """Multiple `--preset` options should all be accepted."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--preset",
                    "opencode",
                    "--preset",
                    "opencode",
                    "echo",
                    "test",
                ],
            )
            assert result.exit_code == 0

    def test_shell_preset_command_takes_precedence(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--preset` with explicit command should use command, not preset default."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with cli_runner.isolated_filesystem(temp_dir=repo_root_path):
            result = cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--preset",
                    "opencode",
                    "echo",
                    "override",
                ],
            )
            assert result.exit_code == 0

    def test_shell_preset_default_command_used_when_no_args(
        self, cli_runner: click.testing.CliRunner, tmp_workspace: Workspace
    ) -> None:
        """`--preset` should inject the preset's default command when no args given."""
        repo_root_path = tmp_workspace.project.repo_root_path
        with (
            cli_runner.isolated_filesystem(temp_dir=repo_root_path),
            patch("arborinth.workspace.logic.Workspace.shell") as mock_shell,
        ):
            mock_shell.return_value = type("Proc", (), {"returncode": 0})()
            cli_runner.invoke(
                main,
                [
                    "shell",
                    tmp_workspace.name,
                    "--preset",
                    "opencode",
                ],
            )
            mock_shell.assert_called_once()
            _call_args, _call_kwargs = mock_shell.call_args
            assert _call_kwargs.get("args") == ("opencode",)
