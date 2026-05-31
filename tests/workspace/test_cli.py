"""Tests for the workspace CLI module."""

from __future__ import annotations

import typing

from arborinth.workspace import cli

if typing.TYPE_CHECKING:
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
