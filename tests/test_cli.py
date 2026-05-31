"""Test module for the Arborinth CLI."""

import click.testing

from arborinth.cli import main


def test_main_no_args(cli_runner: click.testing.CliRunner) -> None:
    """Main command group with no args should exit with non-zero exit code."""
    result = cli_runner.invoke(main, [])
    assert result.exit_code != 0
    assert "Usage:" in result.stderr


def test_main_help(cli_runner: click.testing.CliRunner) -> None:
    """--help should display help message to stdout."""
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Safely run untrusted code" in result.stdout
    assert "Usage:" in result.stdout


def test_main_version(cli_runner: click.testing.CliRunner) -> None:
    """--version should show correct program name."""
    result = cli_runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("arborinth,")
