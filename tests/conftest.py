"""Pytest configuration and fixtures for Arborinth tests."""

import pathlib
import subprocess

import click.testing
import pytest

from arborinth import Project, Workspace

from . import generate_random_string


@pytest.fixture
def cli_runner() -> click.testing.CliRunner:
    """Create a Click CLI test runner."""
    return click.testing.CliRunner()


@pytest.fixture
def tmp_git_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary directory initialized as a git repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


@pytest.fixture
def tmp_project(tmp_git_repo: pathlib.Path) -> Project:
    """Create a `Project` for the temporary git repository."""
    return Project(workdir=tmp_git_repo)


@pytest.fixture
def tmp_workspace(tmp_project: Project) -> Workspace:
    """Create a random `Workspace` in a temporary `Project`."""
    return tmp_project.create_workspace(generate_random_string())
