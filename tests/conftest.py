"""Pytest configuration and fixtures for Arborinth tests."""

import click.testing
import pytest


@pytest.fixture
def cli_runner() -> click.testing.CliRunner:
    """Create a Click CLI test runner."""
    return click.testing.CliRunner()
