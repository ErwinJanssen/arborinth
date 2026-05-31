"""Arborinth command line interface."""

import click

from arborinth.project.cli import project


@click.group()
@click.version_option(prog_name="arborinth")
def main() -> None:
    """Safely run untrusted code on your repository in isolated environments."""


main.add_command(project)
