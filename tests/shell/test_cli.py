"""Tests for the shell CLI module."""

from __future__ import annotations

import typing

from arborinth.cli import main

if typing.TYPE_CHECKING:
    import click.testing


class TestShellCommand:
    """Tests for the `shell` command."""

    def test_shell_help(self, cli_runner: click.testing.CliRunner) -> None:
        """--help should display help message for `shell` command."""
        result = cli_runner.invoke(main, ["shell", "--help"])
        assert result.exit_code == 0
        assert "Run a shell in an isolated environment" in result.stdout
        assert "Usage:" in result.stdout
