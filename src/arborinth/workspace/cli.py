"""CLI for Arborinth's `workspace` module.

This module provides the command-line interface for workspace-related operations.
"""

import click


@click.group()
def workspace() -> None:
    """Manage Arborinth workspaces.

    A workspace is an isolated clone of your repository where untrusted code
    can perform operations without affecting the original repository.
    """
