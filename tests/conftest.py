"""Pytest configuration and fixtures for Arborinth tests."""

import pathlib
import subprocess

import click.testing
import pytest


@pytest.fixture
def cli_runner() -> click.testing.CliRunner:
    """Create a Click CLI test runner."""
    return click.testing.CliRunner()


@pytest.fixture
def tmp_git_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary directory initialized as a git repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path
