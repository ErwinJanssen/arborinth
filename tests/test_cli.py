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
    assert "project" in result.stdout
    assert "workspace" in result.stdout


def test_main_version(cli_runner: click.testing.CliRunner) -> None:
    """--version should show correct program name."""
    result = cli_runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("arborinth,")


def test_main_version_format(cli_runner: click.testing.CliRunner) -> None:
    """--version should show version in correct format."""
    result = cli_runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    # Should contain version number
    assert ", version " in result.stdout or "v" in result.stdout.lower()
