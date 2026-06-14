"""Arborinth command line interface."""

import pathlib

import click

from arborinth import Project
from arborinth.project.cli import project
from arborinth.shell.cli import shell
from arborinth.workspace.cli import workspace


@click.group()
@click.option(
    "--workdir",
    "-C",
    type=click.Path(
        path_type=pathlib.Path,
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    default=".",
    help="Working directory within the Git repository.",
)
@click.version_option(prog_name="arborinth")
@click.pass_context
def main(ctx: click.Context, workdir: pathlib.Path) -> None:
    """Safely run untrusted code on your repository in isolated environments."""
    ctx.obj = Project(workdir=workdir)


main.add_command(project)
main.add_command(shell)
main.add_command(workspace)
