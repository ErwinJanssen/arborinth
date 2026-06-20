"""Tests for the shell logic module."""

from __future__ import annotations

import subprocess
import typing

import pytest

from arborinth.shell import BwrapJail, Jail, JailBackend, JailConfig, MountSpec, MountType, NoneJail

if typing.TYPE_CHECKING:
    import pathlib


class TestMountSpec:
    """Tests for the `MountSpec` dataclass."""

    def test_from_spec_ro_bind_same_path(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse ro:dest correctly."""
        dest = tmp_path / "dest"
        spec = f"ro:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.RO
        assert mount.source is None
        assert mount.dest == dest

    def test_from_spec_rw_bind_same_path(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse rw:source correctly."""
        dest = tmp_path / "dest"
        spec = f"rw:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.RW
        assert mount.source is None
        assert mount.dest == dest

    def test_from_spec_ro_bind_different_paths(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse ro:source:dest correctly."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        spec = f"ro:{source}:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.RO
        assert mount.source == source
        assert mount.dest == dest

    def test_from_spec_tmpfs(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse tmpfs:dest correctly."""
        dest = tmp_path / "tmpfs_dest"
        spec = f"tmpfs:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.TMPFS
        assert mount.source is None
        assert mount.dest == dest

    def test_from_spec_dev(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse dev:dest correctly."""
        dest = tmp_path / "dev_dest"
        spec = f"dev:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.DEV
        assert mount.source is None
        assert mount.dest == dest

    def test_from_spec_proc(self, tmp_path: pathlib.Path) -> None:
        """`MountSpec.from_spec` should parse proc:dest correctly."""
        dest = tmp_path / "proc_dest"
        spec = f"proc:{dest}"
        mount = MountSpec.from_spec(spec)

        assert mount.mount_type == MountType.PROC
        assert mount.source is None
        assert mount.dest == dest

    def test_from_spec_invalid_type(self) -> None:
        """`MountSpec.from_spec` should raise ValueError for invalid type."""
        with pytest.raises(ValueError, match="Invalid mount type"):
            MountSpec.from_spec("invalid:/path")

    def test_from_spec_invalid_format(self) -> None:
        """`MountSpec.from_spec` should raise ValueError for invalid format."""
        with pytest.raises(ValueError, match="Invalid mount spec, too few parts"):
            MountSpec.from_spec("ro")

    def test_from_spec_three_parts_invalid_type(self) -> None:
        """`MountSpec.from_spec` should raise ValueError for unsupported source."""
        with pytest.raises(ValueError, match="only supports a destination"):
            MountSpec.from_spec("tmpfs:/source:/dest")


class TestNoneJail:
    """Tests for the `NoneJail` class."""

    def test_is_instance_of_jail(self, tmp_path: pathlib.Path) -> None:
        """`NoneJail` should be an instance of `Jail`."""
        jail = NoneJail(workdir_path=tmp_path)
        assert isinstance(jail, Jail)

    def test_run_with_command(self, tmp_path: pathlib.Path) -> None:
        """`NoneJail.run` should execute a command in the jail's workdir."""
        jail = NoneJail(workdir_path=tmp_path)
        args = ["echo", "test"]

        proc = jail.run(args=args)

        assert isinstance(proc, subprocess.CompletedProcess)
        assert proc.args == args
        assert proc.returncode == 0

    def test_run_with_no_args_uses_default_shell(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`NoneJail.run` with no args should use default shell."""
        jail = NoneJail(workdir_path=tmp_path)

        # Set a specific SHELL to test the default behavior
        monkeypatch.setenv("SHELL", "/bin/sh")

        proc = jail.run(args=None)

        assert proc.args == ["/bin/sh"]
        assert proc.returncode == 0

    def test_run_runs_in_specified_workdir(self, tmp_path: pathlib.Path) -> None:
        """`NoneJail.run` should run command in the jail's workdir."""
        jail = NoneJail(workdir_path=tmp_path)

        # Create a test file in the workdir
        test_file = tmp_path / "test_file.txt"
        args = ["touch", "test_file.txt"]

        proc = jail.run(args=args)

        assert proc.returncode == 0
        assert test_file.exists()

    def test_run_with_invalid_command_raises(self, tmp_path: pathlib.Path) -> None:
        """`NoneJail.run` with invalid command should raise FileNotFoundError."""
        jail = NoneJail(workdir_path=tmp_path)

        with pytest.raises(FileNotFoundError, match="No such file"):
            jail.run(args=["nonexistent_command_xyz"])

    def test_build_command_with_args_returns_args_as_is(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`NoneJail.build_command` with args should return them unchanged."""
        jail = NoneJail(workdir_path=tmp_path)
        args = ["echo", "hello", "world"]

        result = jail.build_command(args=args)

        assert result == args

    def test_build_command_with_no_args_uses_default_shell(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`NoneJail.build_command` with no args should use default shell."""
        jail = NoneJail(workdir_path=tmp_path)

        # Set a specific SHELL to test the default behavior
        monkeypatch.setenv("SHELL", "/bin/sh")

        result = jail.build_command(args=None)

        assert result == ["/bin/sh"]

    def test_build_command_with_no_shell_env_var_uses_fallbacks(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`NoneJail.build_command` with no SHELL env var should use fallbacks."""
        jail = NoneJail(workdir_path=tmp_path)

        # Unset SHELL to test fallback behavior
        monkeypatch.delenv("SHELL", raising=False)

        result = jail.build_command(args=None)

        # Should fall back to bash or sh (may be full path)
        assert result[0].endswith(("bash", "sh"))
        assert len(result) == 1

    def test_build_command_with_no_shell_available_raises(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`NoneJail.build_command` with no shell available should raise."""
        jail = NoneJail(workdir_path=tmp_path)

        # Unset SHELL and mock shutil.which to return None
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.setattr("shutil.which", lambda _: None)

        with pytest.raises(FileNotFoundError, match="No shell binary available"):
            jail.build_command(args=None)


class TestJailConfig:
    """Tests for the `JailConfig` dataclass."""

    def test_default_values(self) -> None:
        """`JailConfig` should have sensible defaults."""
        config = JailConfig()

        assert config.workdir_path is None
        assert config.project_root_path is None
        assert config.home_path is None
        assert config.additional_mounts == []
        assert config.hide_home is True
        assert config.expose_path_entries is True

    def test_custom_values(self, tmp_path: pathlib.Path) -> None:
        """`JailConfig` should accept custom values."""
        project_root = tmp_path / "project"
        home = tmp_path / "home"
        ro_path = tmp_path / "ro"
        rw_path = tmp_path / "rw"

        config = JailConfig(
            workdir_path=tmp_path,
            project_root_path=project_root,
            home_path=home,
            additional_mounts=[
                MountSpec(mount_type=MountType.RO, source=ro_path, dest=ro_path),
                MountSpec(mount_type=MountType.RW, source=rw_path, dest=rw_path),
            ],
            hide_home=False,
            expose_path_entries=False,
        )

        assert config.workdir_path == tmp_path
        assert config.project_root_path == project_root
        assert config.home_path == home
        assert len(config.additional_mounts) == 2
        assert config.hide_home is False
        assert config.expose_path_entries is False

    def test_merge_basic(self, tmp_path: pathlib.Path) -> None:
        """`JailConfig` merge should combine values correctly."""
        config1 = JailConfig(
            workdir_path=tmp_path / "workdir1",
            additional_mounts=[
                MountSpec(mount_type=MountType.RO, source=tmp_path / "ro1", dest=tmp_path / "ro1"),
            ],
        )
        config2 = JailConfig(
            additional_mounts=[
                MountSpec(mount_type=MountType.RO, source=tmp_path / "ro2", dest=tmp_path / "ro2"),
            ],
            hide_home=False,
        )

        merged = config1 | config2

        assert merged.workdir_path == tmp_path / "workdir1"
        assert len(merged.additional_mounts) == 2
        assert merged.hide_home is False

    def test_merge_additional_mounts_appends(self, tmp_path: pathlib.Path) -> None:
        """`JailConfig.__or__` should append additional_mounts."""
        mount1 = MountSpec(mount_type=MountType.RO, source=tmp_path / "m1", dest=tmp_path / "m1")
        mount2 = MountSpec(mount_type=MountType.RW, source=tmp_path / "m2", dest=tmp_path / "m2")

        config1 = JailConfig(additional_mounts=[mount1])
        config2 = JailConfig(additional_mounts=[mount2])

        merged = config1 | config2

        assert len(merged.additional_mounts) == 2
        assert merged.additional_mounts[0] == mount1
        assert merged.additional_mounts[1] == mount2


class TestJailBackend:
    """Tests for the `JailBackend` enum."""

    def test_none_backend_returns_none_jail_class(self) -> None:
        """`JailBackend.NONE.value` should return the `NoneJail` class."""
        assert JailBackend.NONE.value is NoneJail

    def test_none_backend_instantiates_none_jail(self, tmp_path: pathlib.Path) -> None:
        """`JailBackend.NONE.value()` should instantiate a `NoneJail`."""
        instance = JailBackend.NONE.value(workdir_path=tmp_path)
        assert isinstance(instance, NoneJail)
        assert instance.workdir_path == tmp_path

    def test_bwrap_backend_returns_bwrap_jail_class(self) -> None:
        """`JailBackend.BWRAP.value` should return the `BwrapJail` class."""
        assert JailBackend.BWRAP.value is BwrapJail

    def test_bwrap_backend_instantiates_bwrap_jail(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`JailBackend.BWRAP.value()` should instantiate a `BwrapJail`."""
        instance = JailBackend.BWRAP.value(workdir_path=tmp_path)
        assert isinstance(instance, BwrapJail)
        assert instance.workdir_path == tmp_path


class TestBwrapJail:
    """Tests for the `BwrapJail` class."""

    def test_is_instance_of_jail(self, tmp_path: pathlib.Path) -> None:
        """`BwrapJail` should be an instance of `Jail`."""
        jail = BwrapJail(workdir_path=tmp_path)
        assert isinstance(jail, Jail)

    def test_bwrap_not_available_raises(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`BwrapJail.run` should raise FileNotFoundError if bwrap is not available."""
        # Mock shutil.which to return None for bwrap
        monkeypatch.setattr(
            "shutil.which", lambda x: None if x == "bwrap" else "/usr/bin/" + x
        )

        jail = BwrapJail(workdir_path=tmp_path)

        with pytest.raises(FileNotFoundError, match="bwrap.*not installed"):
            jail.run(args=["echo", "test"])

    def test_default_parameters(self, tmp_path: pathlib.Path) -> None:
        """`BwrapJail` should have sensible default parameters."""
        jail = BwrapJail(workdir_path=tmp_path)

        assert jail.workdir_path == tmp_path
        assert jail.project_root_path is None
        assert jail.home_path is None
        assert jail.additional_mounts == []
        assert jail.hide_home is True
        assert jail.expose_path_entries is True

    def test_build_bwrap_args_includes_workdir(self, tmp_path: pathlib.Path) -> None:
        """`BwrapJail._build_bwrap_args` should include workdir as bind."""
        jail = BwrapJail(workdir_path=tmp_path)
        args = jail._build_bwrap_args()

        assert "--bind" in args
        assert str(tmp_path) in args

    def test_build_bwrap_args_includes_basic_mounts(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`BwrapJail._build_bwrap_args` should include basic filesystem mounts."""
        jail = BwrapJail(workdir_path=tmp_path)
        args = jail._build_bwrap_args()

        # Should have basic bwrap options
        assert "bwrap" in args
        assert "--unshare-all" in args
        assert "--die-with-parent" in args
        assert "--new-session" in args

    def test_build_bwrap_args_includes_git_dir(
        self, tmp_path: pathlib.Path, tmp_git_repo: pathlib.Path
    ) -> None:
        """`BwrapJail._build_bwrap_args` should include .git as read-only."""
        jail = BwrapJail(workdir_path=tmp_path, project_root_path=tmp_git_repo)
        args = jail._build_bwrap_args()

        git_dir = tmp_git_repo / ".git"
        assert "--ro-bind" in args
        assert str(git_dir) in args
