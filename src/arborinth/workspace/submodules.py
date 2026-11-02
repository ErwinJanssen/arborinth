"""Logic for initializing Git submodules in workspace clones.

A plain Git clone does not initialize submodules: it only creates empty
directories where the working trees of the submodules would be. This
module initializes the submodules of a workspace clone, nested ones
included, from the local Git object stores of the original repository,
so that no network access is needed.

The object store of a submodule is a Git directory of its own, kept under
the `modules/` subdirectory of its parent repository's Git directory,
keyed by the submodule's name, which can differ from its path. The store
of a nested submodule lives under the `modules/` subdirectory of its
parent's store.

Two invariants hold throughout. First, each submodule is cloned from its
store over the `file://` transport: `git submodule update` has no
`--no-local` passthrough, and a plain path would let Git hardlink the
store's object files, so a process confined to the workspace could
corrupt the original repository's object store by writing to the shared
files. Second, the `protocol.file.allow` relaxation this needs is passed
per invocation only and never written to any configuration file, since
untrusted processes run Git in the clone later.
"""

from __future__ import annotations

import dataclasses
import typing
import warnings

from arborinth import _util

if typing.TYPE_CHECKING:
    import pathlib

    from arborinth.workspace import Workspace


@dataclasses.dataclass
class Submodule:
    """A Git submodule of the original repository.

    Attributes:
        name: The name of the submodule, the key under which it is recorded
            in the `.gitmodules` file of its parent repository.
        path: The path of the submodule, relative to the working tree of
            its parent repository.
        store_path: The absolute path of the submodule's local object store
            in the original repository: the `modules/<name>` subdirectory of
            the parent repository's Git directory.
        children: The submodules of the submodule, nested one level deeper.
    """

    name: str
    path: str
    store_path: pathlib.Path
    children: list[Submodule] = dataclasses.field(default_factory=list)


def enumerate_submodules(
    repo_root_path: pathlib.Path,
) -> tuple[list[Submodule], list[tuple[str, pathlib.Path]]]:
    """Enumerate the submodules of a repository.

    The top-level submodules are read from the repository's `.gitmodules`
    file, and the nested ones from the `.gitmodules` files of the
    repository's submodule working trees. A submodule whose local object
    store is missing in the original repository (it was never initialized
    there) is skipped together with its whole subtree and returned as
    skipped; the caller reports it.

    Args:
        repo_root_path: The root path of the original repository.

    Returns:
        The top-level submodules that have a local object store, each with
        its own submodules, and the names and store paths of those that do
        not.

    Raises:
        RuntimeError: If a `.gitmodules` file cannot be read.
    """
    skipped: list[tuple[str, pathlib.Path]] = []
    roots = _enumerate_submodules(repo_root_path, repo_root_path / ".git", skipped)
    return roots, skipped


def _enumerate_submodules(
    worktree_path: pathlib.Path,
    store_path: pathlib.Path,
    skipped: list[tuple[str, pathlib.Path]],
) -> list[Submodule]:
    """Enumerate the submodules of one level of a repository.

    Args:
        worktree_path: The working tree whose `.gitmodules` file lists the
            submodules to enumerate.
        store_path: The Git directory whose `modules/` subdirectory holds
            the local object stores of those submodules.
        skipped: Collected across all levels: the names and store paths of
            the submodules without a local object store.

    Returns:
        The submodules that have a local object store, each with its own
        submodules.

    Raises:
        RuntimeError: If the `.gitmodules` file cannot be read.
    """
    gitmodules_path = worktree_path / ".gitmodules"
    if not gitmodules_path.exists():
        return []

    submodules = []
    for name, path in _parse_gitmodules(gitmodules_path).items():
        submodule_store_path = store_path / "modules" / name
        if not (submodule_store_path / "objects").is_dir():
            skipped.append((name, submodule_store_path))
            continue
        submodules.append(
            Submodule(
                name=name,
                path=path,
                store_path=submodule_store_path,
                children=_enumerate_submodules(
                    worktree_path / path, submodule_store_path, skipped
                ),
            )
        )
    return submodules


def initialize_submodules(workspace: Workspace) -> None:
    """Initialize the submodules of a workspace clone.

    The submodules are enumerated from the original repository and
    initialized breadth-first, level by level. For each level, every
    submodule's parent clone gets a `submodule.<name>.url` override that
    points at the submodule's local object store, and `git submodule
    update --init` is run in that parent. The overrides for a level are
    written into the level's parent clone, which only exists once that
    parent has been initialized, hence the level-by-level order. The
    overrides rely on the two invariants documented in the module
    docstring.

    A submodule whose local store is missing in the original repository is
    skipped together with its whole subtree and reported with a warning; it
    is never passed to Git, so it cannot fall back to its recorded URL and
    the network.

    Args:
        workspace: The workspace whose clone's submodules to initialize.

    Raises:
        RuntimeError: If Git is not installed or a Git command fails.
    """
    roots, skipped = enumerate_submodules(workspace.project.repo_root_path)

    # The skipped submodules are reported here rather than during
    # enumeration, so that the warning is attributed to the caller of this
    # function and can name the workspace.
    for name, store_path in skipped:
        warnings.warn(
            f"Submodule '{name}' of workspace '{workspace.name}' has no "
            f"local object store at {store_path}; skipping it and its "
            f"submodules.",
            stacklevel=2,
        )
    if not roots:
        return

    # Initialize breadth-first, level by level. Each entry pairs the working
    # tree of a parent clone with the submodules to initialize in it; the
    # first level's parent is the workspace clone itself.
    level: list[tuple[pathlib.Path, list[Submodule]]] = [
        (workspace.workdir_path, roots)
    ]
    while level:
        next_level: list[tuple[pathlib.Path, list[Submodule]]] = []
        for parent_worktree_path, submodules in level:
            _initialize_level(workspace, parent_worktree_path, submodules)
            for submodule in submodules:
                worktree_path = parent_worktree_path / submodule.path
                if submodule.children:
                    next_level.append((worktree_path, submodule.children))
        level = next_level


def _initialize_level(
    workspace: Workspace,
    parent_worktree_path: pathlib.Path,
    submodules: list[Submodule],
) -> None:
    """Initialize the submodules of one level in their parent clone.

    Args:
        workspace: The workspace whose clone's submodules to initialize.
        parent_worktree_path: The working tree of the parent clone.
        submodules: The submodules to initialize in the parent clone.

    Raises:
        RuntimeError: If Git is not installed or a Git command fails.
    """
    for submodule in submodules:
        # Point the submodule at its local object store in the original
        # repository. The `file://` form is load-bearing; see the module
        # docstring.
        _util.run_git(
            [
                "config",
                "--local",
                f"submodule.{submodule.name}.url",
                f"file://{submodule.store_path}",
            ],
            cwd=parent_worktree_path,
            error_message=(
                f"Failed to configure the submodules of workspace '{workspace.name}'"
            ),
        )

    # The `protocol.file.allow` relaxation is passed per invocation only
    # (see the module docstring). Only submodules with a local object
    # store are passed to Git, so the skipped ones are never initialized
    # from their recorded URLs.
    _util.run_git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "update",
            "--init",
            "--",
            *(submodule.path for submodule in submodules),
        ],
        cwd=parent_worktree_path,
        error_message=(
            f"Failed to initialize the submodules of workspace '{workspace.name}'"
        ),
    )


def _parse_gitmodules(gitmodules_path: pathlib.Path) -> dict[str, str]:
    """Map submodule names to paths, read from a `.gitmodules` file.

    The file is read with Git itself, so the exact configuration file syntax
    (quoting, escaping) is handled the same way Git handles it.

    Args:
        gitmodules_path: The path of the `.gitmodules` file to read.

    Returns:
        A dictionary that maps each submodule's name to its path.

    Raises:
        RuntimeError: If the `.gitmodules` file cannot be read.
    """
    result = _util.run_git(
        ["config", "--file", str(gitmodules_path), "--null", "--list"],
        error_message="Failed to read the submodules",
    )

    paths = {}
    for entry in result.stdout.split("\0"):
        # Each entry is a key and a value, separated by a newline (see the
        # `--null` option in git-config(1)). The last entry is empty.
        key, separator, value = entry.partition("\n")
        if not separator:
            continue
        # A key has the form `submodule.<name>.path`. Section names and
        # option names cannot contain dots, so the name is everything
        # between the first and the last dot.
        parts = key.split(".")
        if len(parts) < 3 or parts[0] != "submodule" or parts[-1] != "path":  # noqa: PLR2004
            continue
        paths[".".join(parts[1:-1])] = value
    return paths
