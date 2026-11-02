"""Tests for submodule initialization in workspace clones."""

from __future__ import annotations

import os
import shutil
import subprocess
import typing
import warnings

import pytest

from arborinth.project import logic

if typing.TYPE_CHECKING:
    import pathlib

# Environment for the Git commands of the test fixtures: they must not
# depend on the host system's Git configuration. Commit identities come
# from repo-local configuration.
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
}


def run_git(cwd: pathlib.Path, *args: str) -> str:
    """Run a Git command in a fixture repository and return its output."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_local_config(cwd: pathlib.Path, key: str) -> str | None:
    """Read a local configuration value, or `None` when it is not set."""
    result = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=cwd,
        env=GIT_ENV,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def init_repo(path: pathlib.Path) -> None:
    """Create a Git repository with a commit identity of its own."""
    path.mkdir(parents=True)
    run_git(path, "init")
    run_git(path, "config", "--local", "user.name", "Repo User")
    run_git(path, "config", "--local", "user.email", "repo@example.com")


def commit(path: pathlib.Path, message: str) -> None:
    """Commit all changes in a fixture repository."""
    run_git(path, "add", "-A")
    run_git(path, "commit", "-m", message)


def add_submodule(
    repo_path: pathlib.Path, name: str, source_path: pathlib.Path, path: str
) -> None:
    """Add a repository as a submodule of a fixture repository.

    The submodule is cloned over the `file://` transport, which requires the
    `protocol.file.allow` relaxation.
    """
    run_git(
        repo_path,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "--name",
        name,
        f"file://{source_path}",
        path,
    )


def make_repo_with_submodule(base_path: pathlib.Path) -> pathlib.Path:
    """Create a repository with one initialized submodule named `dep`.

    The submodule is added at the path `dep-dir`, from the repository `dep`
    next to it. After the submodule is added, the source repository moves on
    with another commit, so the gitlink recorded in the main repository no
    longer points at its HEAD.
    """
    dep_path = base_path / "dep"
    init_repo(dep_path)
    (dep_path / "dep.txt").write_text("dep-content\n")
    commit(dep_path, "dep")

    repo_path = base_path / "main"
    init_repo(repo_path)
    (repo_path / "main.txt").write_text("main-content\n")
    commit(repo_path, "main")
    add_submodule(repo_path, "dep", dep_path, "dep-dir")
    commit(repo_path, "add submodule")

    # Move the source repository past the pinned gitlink.
    (dep_path / "dep.txt").write_text("dep-content-2\n")
    commit(dep_path, "dep, second commit")
    return repo_path


def store_files(store_path: pathlib.Path) -> list[pathlib.Path]:
    """List the files in a module store's object store, deterministically."""
    objects_path = store_path / "objects"
    return sorted(path for path in objects_path.rglob("*") if path.is_file())


def make_repo_with_nested_submodules(base_path: pathlib.Path) -> pathlib.Path:
    """Create a repository whose submodule has a submodule of its own.

    The submodule `outer` is added at the path `vendor/outer`, from the
    repository `outer` next to the main repository. The `outer` repository
    itself has the submodule `inner`, added at the path `lib/inner` from the
    repository `inner`. All submodules are initialized in the main
    repository, so that it has local object stores for them.
    """
    inner_path = base_path / "inner"
    init_repo(inner_path)
    (inner_path / "inner.txt").write_text("inner-content\n")
    commit(inner_path, "inner")

    outer_path = base_path / "outer"
    init_repo(outer_path)
    (outer_path / "outer.txt").write_text("outer-content\n")
    commit(outer_path, "outer")
    add_submodule(outer_path, "inner", inner_path, "lib/inner")
    commit(outer_path, "add inner submodule")

    repo_path = base_path / "main"
    init_repo(repo_path)
    (repo_path / "main.txt").write_text("main-content\n")
    commit(repo_path, "main")
    add_submodule(repo_path, "outer", outer_path, "vendor/outer")
    commit(repo_path, "add outer submodule")

    # Initialize the nested submodule in the original repository, so that it
    # has a local object store there as well.
    run_git(
        repo_path,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "update",
        "--init",
        "--recursive",
    )
    return repo_path


class TestTopLevelSubmodules:
    """Tests for initializing top-level submodules in workspace clones."""

    def test_submodule_initialized_at_pinned_sha(self, tmp_path: pathlib.Path) -> None:
        """The clone should contain the submodule at the pinned gitlink SHA.

        A plain clone leaves the submodule directory empty; the submodule's
        working tree must be checked out in the workspace clone, at the
        commit recorded by the superproject's gitlink.
        """
        repo_path = make_repo_with_submodule(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        # The content is that of the pinned commit, not of the source
        # repository's HEAD, which has moved on since.
        content_path = workspace.workdir_path / "dep-dir" / "dep.txt"
        assert content_path.read_text() == "dep-content\n"

        # The submodule clone's HEAD is the gitlink SHA recorded in the
        # superproject's tree.
        gitlink_sha = run_git(
            workspace.workdir_path, "rev-parse", "HEAD:dep-dir"
        ).strip()
        submodule_sha = run_git(
            workspace.workdir_path / "dep-dir", "rev-parse", "HEAD"
        ).strip()
        assert submodule_sha == gitlink_sha

    def test_submodule_cloned_from_local_store(self, tmp_path: pathlib.Path) -> None:
        """The submodule should be cloned from the original's object store.

        The clone's local configuration gets a `file://` URL override for the
        submodule, pointing at the original repository's module store.
        """
        repo_path = make_repo_with_submodule(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        store_path = repo_path / ".git" / "modules" / "dep"
        assert (
            get_local_config(workspace.workdir_path, "submodule.dep.url")
            == f"file://{store_path}"
        )
        # The submodule has its own object store inside the workspace clone.
        assert (workspace.workdir_path / ".git" / "modules" / "dep").is_dir()

    def test_initialized_submodules_do_not_warn(self, tmp_path: pathlib.Path) -> None:
        """Submodules with a local store should not be reported as skipped."""
        repo_path = make_repo_with_submodule(tmp_path)
        project = logic.Project(workdir=repo_path)

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            project.create_workspace("ws")

        assert not record

    def test_missing_store_skipped_with_warning(self, tmp_path: pathlib.Path) -> None:
        """A submodule without a local store should be skipped with a warning.

        The original repository never initialized it, so the workspace clone
        must not initialize it either: no URL override is written, so Git
        never touches its recorded URL and there is no network fallback. The
        other submodules are still initialized.
        """
        repo_path = make_repo_with_submodule(tmp_path)

        # A second, healthy submodule.
        dep2_path = tmp_path / "dep2"
        init_repo(dep2_path)
        (dep2_path / "dep2.txt").write_text("dep2-content\n")
        commit(dep2_path, "dep2")
        add_submodule(repo_path, "kept", dep2_path, "kept-dir")
        commit(repo_path, "add kept submodule")

        # Simulate `dep` never being initialized in the original repository.
        shutil.rmtree(repo_path / ".git" / "modules" / "dep")
        shutil.rmtree(repo_path / "dep-dir")

        project = logic.Project(workdir=repo_path)
        with pytest.warns(
            UserWarning,
            match="Submodule 'dep' of workspace 'ws' has no local object store",
        ):
            workspace = project.create_workspace("ws")

        # The skipped submodule is left uninitialized.
        assert not (workspace.workdir_path / "dep-dir" / "dep.txt").exists()
        assert get_local_config(workspace.workdir_path, "submodule.dep.url") is None

        # The healthy submodule is initialized.
        content_path = workspace.workdir_path / "kept-dir" / "dep2.txt"
        assert content_path.read_text() == "dep2-content\n"
        kept_store_path = repo_path / ".git" / "modules" / "kept"
        assert (
            get_local_config(workspace.workdir_path, "submodule.kept.url")
            == f"file://{kept_store_path}"
        )

    def test_no_shared_objects_with_original_store(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Submodule stores must not share object files with the original.

        A clone with a plain path would hardlink the objects of the original
        store, and a process confined to the workspace could then corrupt the
        original repository's object store by writing to the shared files. The
        `file://` transport copies the objects instead, so the original
        store's files are untouched.
        """
        repo_path = make_repo_with_submodule(tmp_path)
        original_files = store_files(repo_path / ".git" / "modules" / "dep")
        assert original_files
        stat_before = original_files[0].stat()

        project = logic.Project(workdir=repo_path)
        workspace = project.create_workspace("ws")

        # The original store's object file is untouched: same inode, and no
        # additional hardlink to it was created.
        stat_after = original_files[0].stat()
        assert stat_after.st_ino == stat_before.st_ino
        assert stat_after.st_nlink == stat_before.st_nlink

        # The workspace clone got its own copies of the objects: no file of
        # the clone's store shares an inode with the original store.
        clone_store_path = workspace.workdir_path / ".git" / "modules" / "dep"
        clone_files = store_files(clone_store_path)
        assert clone_files
        original_inodes = {
            (path.stat().st_dev, path.stat().st_ino) for path in original_files
        }
        clone_inodes = {
            (path.stat().st_dev, path.stat().st_ino) for path in clone_files
        }
        assert not original_inodes & clone_inodes

    def test_protocol_file_allow_not_persisted(self, tmp_path: pathlib.Path) -> None:
        """The `protocol.file.allow` relaxation must not be persisted.

        Untrusted processes run Git in the workspace clone later, and
        persisting the relaxation would broaden their Git attack surface. It
        is passed as a per-invocation `-c` option only.
        """
        repo_path = make_repo_with_submodule(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        for file_path in (workspace.workdir_path / ".git").rglob("*"):
            if file_path.is_file():
                assert b"protocol.file.allow" not in file_path.read_bytes()

    def test_submodule_init_failure_cleans_up_workspace(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A failing submodule initialization should clean up the workspace.

        Git fails when the store has no objects to serve; the workspace
        directory is then removed, like for the other steps of workspace
        creation.
        """
        repo_path = make_repo_with_submodule(tmp_path)
        # Break the store's object store, but leave it detectable as a store.
        for file_path in store_files(repo_path / ".git" / "modules" / "dep"):
            file_path.unlink()

        project = logic.Project(workdir=repo_path)

        with pytest.raises(RuntimeError, match="Failed to initialize the submodules"):
            project.create_workspace("ws")

        workspace_path = project.workspace_root_path / "ws"
        assert not workspace_path.exists()


class TestNestedSubmodules:
    """Tests for initializing nested submodules in workspace clones."""

    def test_nested_submodule_initialized(self, tmp_path: pathlib.Path) -> None:
        """Nested submodules should be initialized after their parent.

        The nested submodule's working tree must be checked out in the
        parent submodule's clone, at the gitlink SHA pinned by the parent,
        with its own object store under the parent's.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        outer_workdir_path = workspace.workdir_path / "vendor" / "outer"
        content_path = outer_workdir_path / "outer.txt"
        assert content_path.read_text() == "outer-content\n"

        inner_workdir_path = outer_workdir_path / "lib" / "inner"
        content_path = inner_workdir_path / "inner.txt"
        assert content_path.read_text() == "inner-content\n"

        # The nested submodule's HEAD is the gitlink SHA pinned by its
        # parent.
        gitlink_sha = run_git(outer_workdir_path, "rev-parse", "HEAD:lib/inner").strip()
        inner_sha = run_git(inner_workdir_path, "rev-parse", "HEAD").strip()
        assert inner_sha == gitlink_sha

        # The nested submodule has its own object store in its parent's Git
        # directory, mirroring the layout of the original repository.
        inner_store_path = (
            workspace.workdir_path / ".git" / "modules" / "outer" / "modules" / "inner"
        )
        assert inner_store_path.is_dir()

    def test_nested_url_override_written_into_parent_clone(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The URL overrides of nested submodules belong to the parent clone.

        A nested submodule is initialized by its parent's clone, so the
        override for it is written into the parent clone's local
        configuration, and the superproject clone only has overrides for
        its own submodules.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        outer_workdir_path = workspace.workdir_path / "vendor" / "outer"
        inner_store_path = (
            repo_path / ".git" / "modules" / "outer" / "modules" / "inner"
        )
        assert (
            get_local_config(outer_workdir_path, "submodule.inner.url")
            == f"file://{inner_store_path}"
        )
        outer_store_path = repo_path / ".git" / "modules" / "outer"
        assert (
            get_local_config(workspace.workdir_path, "submodule.outer.url")
            == f"file://{outer_store_path}"
        )
        assert get_local_config(workspace.workdir_path, "submodule.inner.url") is None

    def test_missing_nested_store_skipped_with_warning(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A nested submodule without a store should be skipped with a warning.

        The original repository never initialized it, so the workspace clone
        must not initialize it either. Its parent is still initialized.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        # Simulate `inner` never being initialized in the original
        # repository.
        shutil.rmtree(repo_path / ".git" / "modules" / "outer" / "modules" / "inner")
        shutil.rmtree(repo_path / "vendor" / "outer" / "lib" / "inner")

        project = logic.Project(workdir=repo_path)
        with pytest.warns(
            UserWarning,
            match="Submodule 'inner' of workspace 'ws' has no local object store",
        ):
            workspace = project.create_workspace("ws")

        # The parent submodule is initialized, the skipped one is not.
        outer_workdir_path = workspace.workdir_path / "vendor" / "outer"
        content_path = outer_workdir_path / "outer.txt"
        assert content_path.read_text() == "outer-content\n"
        assert not (outer_workdir_path / "lib" / "inner" / "inner.txt").exists()

    def test_missing_parent_store_skips_whole_subtree(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A missing top-level store should skip its whole subtree.

        The nested submodules of a skipped submodule cannot be enumerated
        without their parent, so exactly one warning is emitted, for the
        parent.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        # Simulate `outer` never being initialized in the original
        # repository, taking its nested submodule with it.
        shutil.rmtree(repo_path / ".git" / "modules" / "outer")
        shutil.rmtree(repo_path / "vendor" / "outer")

        project = logic.Project(workdir=repo_path)
        with pytest.warns(
            UserWarning,
            match="Submodule 'outer' of workspace 'ws' has no local object store",
        ) as record:
            workspace = project.create_workspace("ws")

        assert len(record) == 1
        outer_workdir_path = workspace.workdir_path / "vendor" / "outer"
        assert not (outer_workdir_path / "outer.txt").exists()


class TestSubmoduleOrigins:
    """Tests for the `origin` remotes of submodule clones."""

    def test_submodule_origins_are_relative(self, tmp_path: pathlib.Path) -> None:
        """Submodule origins should be relative paths to the original stores.

        Git stores the overridden absolute `file://` URL of the store as the
        clone's `origin` URL. It must be replaced with a path relative to the
        submodule clone, like the workspace clone's own `origin`, so that the
        remote keeps working when the repository directory is moved.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        project = logic.Project(workdir=repo_path)

        workspace = project.create_workspace("ws")

        outer_workdir_path = workspace.workdir_path / "vendor" / "outer"
        outer_store_path = repo_path / ".git" / "modules" / "outer"
        assert run_git(outer_workdir_path, "remote", "get-url", "origin").strip() == (
            os.path.relpath(outer_store_path, outer_workdir_path)
        )

        inner_workdir_path = outer_workdir_path / "lib" / "inner"
        inner_store_path = (
            repo_path / ".git" / "modules" / "outer" / "modules" / "inner"
        )
        assert run_git(inner_workdir_path, "remote", "get-url", "origin").strip() == (
            os.path.relpath(inner_store_path, inner_workdir_path)
        )

    def test_fetch_works_after_repo_move(self, tmp_path: pathlib.Path) -> None:
        """Submodule remotes should keep working after the repo is moved.

        The `origin` remotes of the submodule clones are registered with
        paths relative to the clones, so they resolve to the original
        repository's module stores in the moved directory, not to the
        directory the workspace was created in.
        """
        repo_path = make_repo_with_nested_submodules(tmp_path)
        project = logic.Project(workdir=repo_path)
        workspace = project.create_workspace("ws")

        moved_path = tmp_path / "moved"
        shutil.move(repo_path, moved_path)
        moved_workdir_path = moved_path / workspace.workdir_path.relative_to(repo_path)

        # `git fetch` from the top-level submodule clone and from the nested
        # submodule clone, which sits in a subdirectory of its parent clone:
        # the relative URLs resolve against each clone's own root, not
        # against the directory the workspace was created in.
        outer_workdir_path = moved_workdir_path / "vendor" / "outer"
        outer_proc = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=outer_workdir_path,
            env=GIT_ENV,
            capture_output=True,
            check=False,
            text=True,
        )
        assert outer_proc.returncode == 0, outer_proc.stderr

        inner_workdir_path = outer_workdir_path / "lib" / "inner"
        inner_proc = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=inner_workdir_path,
            env=GIT_ENV,
            capture_output=True,
            check=False,
            text=True,
        )
        assert inner_proc.returncode == 0, inner_proc.stderr
