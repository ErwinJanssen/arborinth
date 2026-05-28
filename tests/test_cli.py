"""Test module for the Arborinth CLI."""

import click.testing
import pytest

from arborinth.cli import main


@pytest.fixture
def runner() -> click.testing.CliRunner:
    """Create a Click CLI test runner."""
    return click.testing.CliRunner()


def test_main_no_args(runner: click.testing.CliRunner) -> None:
    """Main command group with no args should exit with non-zero exit code."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "Usage:" in result.stderr


def test_main_help(runner: click.testing.CliRunner) -> None:
    """--help should display help message to stdout."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Safely run untrusted code" in result.stdout
    assert "Usage:" in result.stdout


def test_main_version(runner: click.testing.CliRunner) -> None:
    """--version should show correct program name."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("arborinth,")
