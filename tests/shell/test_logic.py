"""Tests for the shell logic module."""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import typing

import pytest

from arborinth.shell import (
    BubblewrapJail,
    Jail,
    JailBackend,
    MountSpec,
    MountType,
    NoneJail,
)

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

    def test_bubblewrap_backend_returns_bubblewrap_jail_class(self) -> None:
        """`JailBackend.BUBBLEWRAP.value` should return the `BubblewrapJail` class."""
        assert JailBackend.BUBBLEWRAP.value is BubblewrapJail

    def test_bubblewrap_backend_instantiates_bubblewrap_jail(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`JailBackend.BUBBLEWRAP.value()` should instantiate a `BubblewrapJail`."""
        instance = JailBackend.BUBBLEWRAP.value(workdir_path=tmp_path)
        assert isinstance(instance, BubblewrapJail)
        assert instance.workdir_path == tmp_path


class TestBubblewrapJail:
    """Tests for the `BubblewrapJail` class."""

    def test_is_instance_of_jail(self, tmp_path: pathlib.Path) -> None:
        """`BubblewrapJail` should be an instance of `Jail`."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        assert isinstance(jail, Jail)

    def test_build_command_with_args(self, tmp_path: pathlib.Path) -> None:
        """`BubblewrapJail.build_command` should return a proper bwrap command."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        args = ["echo", "hello"]

        result = jail.build_command(args=args)

        # Check that bwrap is the first element
        assert result[0] == "bwrap"
        # Check that --unshare-all is present
        assert "--unshare-all" in result
        # Check that workdir is bound read-write
        assert "--bind" in result
        assert str(tmp_path) in result
        # Check that -- separates bwrap options from command
        assert "--" in result
        # Check that the command comes after --
        assert result[result.index("--") + 1 :] == args

    def test_build_command_with_no_args_uses_default_shell(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`BubblewrapJail.build_command` with no args should use default shell."""
        jail = BubblewrapJail(workdir_path=tmp_path)

        # Set a specific SHELL to test the default behavior
        monkeypatch.setenv("SHELL", "/bin/sh")

        result = jail.build_command(args=None)

        # Check that bwrap is the first element
        assert result[0] == "bwrap"
        # Check that -- separator is present
        assert "--" in result
        # Check that default shell comes after --
        assert result[result.index("--") + 1] == "/bin/sh"

    def test_build_command_includes_essential_mounts(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`BubblewrapJail.build_command` should include essential filesystem mounts."""
        jail = BubblewrapJail(workdir_path=tmp_path)

        result = jail.build_command(args=["echo", "test"])

        # Check for essential mounts
        assert "--chdir" in result
        assert str(tmp_path.resolve()) in result
        assert "--ro-bind" in result
        assert "/" in result
        assert "--dev" in result
        assert "/dev" in result
        assert "--proc" in result
        assert "/proc" in result
        assert "--tmpfs" in result
        assert "/tmp" in result  # noqa: S108

    def test_bwrap_not_available_raises(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`BubblewrapJail.run` should raise FileNotFoundError if bwrap missing."""

        # Mock subprocess.run to raise FileNotFoundError for bwrap
        def mock_run(*args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401, ARG001
            """Mock subprocess.run to raise FileNotFoundError for bwrap."""
            message = "[Errno 2] No such file or directory: 'bwrap'"
            raise FileNotFoundError(message)

        monkeypatch.setattr("subprocess.run", mock_run)

        jail = BubblewrapJail(workdir_path=tmp_path)

        with pytest.raises(
            FileNotFoundError, match="No such file or directory: 'bwrap'"
        ):
            jail.run(args=["echo", "test"])


class TestBubblewrapJailIntegration:
    """Integration tests for BubblewrapJail that require bwrap to be installed."""

    @pytest.fixture(autouse=True)
    def skip_without_bwrap(self) -> None:
        """Skip all tests in this class if bwrap is not installed."""
        if shutil.which("bwrap") is None:
            pytest.skip("bubblewrap not installed")

    def test_cannot_write_to_root(self, tmp_path: pathlib.Path) -> None:
        """Writing to root filesystem should fail (it's read-only)."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["touch", "/test_write_denied"])
        assert result.returncode != 0

    def test_cannot_write_to_etc(self, tmp_path: pathlib.Path) -> None:
        """Writing to /etc should fail (it's read-only)."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["touch", "/etc/test_write_denied"])
        assert result.returncode != 0

    def test_can_write_to_workdir(self, tmp_path: pathlib.Path) -> None:
        """Writing to the workdir should succeed (it's read-write)."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        test_file = tmp_path / "test_write_ok"
        result = jail.run(args=["touch", str(test_file)])
        assert result.returncode == 0
        assert test_file.exists()

    def test_can_read_host_filesystem(self, tmp_path: pathlib.Path) -> None:
        """Host filesystem should be readable through the read-only bind."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["cat", "/etc/os-release"])
        assert result.returncode == 0

    def test_tmp_is_tmpfs(self, tmp_path: pathlib.Path) -> None:
        """Verify /tmp is a fresh tmpfs mount inside the sandbox."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        # Write to /tmp in the sandbox
        result = jail.run(args=["touch", "/tmp/test_in_sandbox"])  # noqa: S108
        assert result.returncode == 0
        # /tmp is a tmpfs, so the file exists inside the sandbox
        # We can't easily verify it's isolated from the host /tmp without
        # checking mount info, but the command succeeding confirms /tmp is writable

    def test_proc_isolation(self, tmp_path: pathlib.Path) -> None:
        """Verify PID namespace isolation via /proc."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        # In an isolated PID namespace, /proc/1 should be the init process of
        # the sandbox, which should be a bwrap process.
        result = jail.run(
            # `grep [b]wrap` to avoid matching the grep process itself
            args=["bash", "-c", "cat /proc/1/cmdline | grep --text [b]wrap"]
        )
        assert result.returncode == 0
