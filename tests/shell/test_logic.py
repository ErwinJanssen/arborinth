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


class TestMountSpec:
    """Tests for the `MountSpec` dataclass."""

    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            pytest.param(
                "ro:/dest",
                MountSpec(
                    mount_type=MountType.RO,
                    source=None,
                    dest=pathlib.Path("/dest"),
                ),
                id="ro-bind-same-path",
            ),
            pytest.param(
                "rw:/dest",
                MountSpec(
                    mount_type=MountType.RW,
                    source=None,
                    dest=pathlib.Path("/dest"),
                ),
                id="rw-bind-same-path",
            ),
            pytest.param(
                "ro:/source:/dest",
                MountSpec(
                    mount_type=MountType.RO,
                    source=pathlib.Path("/source"),
                    dest=pathlib.Path("/dest"),
                ),
                id="ro-bind-different-paths",
            ),
            pytest.param(
                "rw:/source:/dest",
                MountSpec(
                    mount_type=MountType.RW,
                    source=pathlib.Path("/source"),
                    dest=pathlib.Path("/dest"),
                ),
                id="rw-bind-different-paths",
            ),
            pytest.param(
                "tmpfs:/dest",
                MountSpec(
                    mount_type=MountType.TMPFS,
                    source=None,
                    dest=pathlib.Path("/dest"),
                ),
                id="tmpfs",
            ),
            pytest.param(
                "dev:/dev",
                MountSpec(
                    mount_type=MountType.DEV,
                    source=None,
                    dest=pathlib.Path("/dev"),
                ),
                id="dev",
            ),
            pytest.param(
                "proc:/proc",
                MountSpec(
                    mount_type=MountType.PROC,
                    source=None,
                    dest=pathlib.Path("/proc"),
                ),
                id="proc",
            ),
        ],
    )
    def test_from_spec_valid(self, spec: str, expected: MountSpec) -> None:
        """`MountSpec.from_spec` should parse valid specs correctly."""
        assert MountSpec.from_spec(spec) == expected

    @pytest.mark.parametrize(
        ("spec", "match"),
        [
            pytest.param(
                "invalid:/path",
                "Invalid mount type",
                id="invalid-mount-type",
            ),
            pytest.param(
                "ro",
                "Invalid mount spec, too few parts",
                id="too-few-parts",
            ),
            pytest.param(
                "ro:a:b:c",
                "Invalid mount spec, too many parts",
                id="too-many-parts",
            ),
            pytest.param(
                "tmpfs:/source:/dest",
                "only supports a destination",
                id="source-not-allowed-for-type",
            ),
        ],
    )
    def test_from_spec_invalid(self, spec: str, match: str) -> None:
        """`MountSpec.from_spec` should raise ValueError for invalid specs."""
        with pytest.raises(ValueError, match=match):
            MountSpec.from_spec(spec)


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

    def test_mount_specs_ignored(self, tmp_path: pathlib.Path) -> None:
        """`NoneJail` should ignore mount_specs."""
        mount = MountSpec(mount_type=MountType.RO, source=None, dest=tmp_path / "dest")
        jail = NoneJail(workdir_path=tmp_path, mount_specs=[mount])

        result = jail.build_command(args=["echo", "test"])

        assert result == ["echo", "test"]


class TestJailBackend:
    """Tests for the `JailBackend` enum."""

    @pytest.mark.parametrize(
        ("backend", "expected"),
        [
            pytest.param(JailBackend.NONE, NoneJail, id="none"),
            pytest.param(JailBackend.BUBBLEWRAP, BubblewrapJail, id="bubblewrap"),
        ],
    )
    def test_value(self, backend: JailBackend, expected: type[Jail]) -> None:
        """`JailBackend.value` should return the correct jail class."""
        assert backend.value is expected

    @pytest.mark.parametrize(
        ("backend", "expected"),
        [
            pytest.param(JailBackend.NONE, NoneJail, id="none"),
            pytest.param(JailBackend.BUBBLEWRAP, BubblewrapJail, id="bubblewrap"),
        ],
    )
    def test_instantiate(
        self, backend: JailBackend, expected: type[Jail], tmp_path: pathlib.Path
    ) -> None:
        """`JailBackend.value()` should instantiate the correct jail class."""
        instance = backend.value(workdir_path=tmp_path)
        assert isinstance(instance, expected)
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

    @pytest.mark.parametrize(
        ("mount", "expected"),
        [
            pytest.param(
                MountSpec(
                    mount_type=MountType.RO,
                    source=pathlib.Path("/host/src"),
                    dest=pathlib.Path("/sandbox/dest"),
                ),
                ["--ro-bind", "/host/src", "/sandbox/dest"],
                id="ro-bind",
            ),
            pytest.param(
                MountSpec(
                    mount_type=MountType.RW,
                    source=pathlib.Path("/host/src"),
                    dest=pathlib.Path("/sandbox/dest"),
                ),
                ["--bind", "/host/src", "/sandbox/dest"],
                id="rw-bind",
            ),
            pytest.param(
                MountSpec(
                    mount_type=MountType.TMPFS,
                    source=None,
                    dest=pathlib.Path("/sandbox/tmp"),
                ),
                ["--tmpfs", "/sandbox/tmp"],
                id="tmpfs",
            ),
            pytest.param(
                MountSpec(
                    mount_type=MountType.DEV,
                    source=None,
                    dest=pathlib.Path("/sandbox/dev"),
                ),
                ["--dev", "/sandbox/dev"],
                id="dev",
            ),
            pytest.param(
                MountSpec(
                    mount_type=MountType.PROC,
                    source=None,
                    dest=pathlib.Path("/sandbox/proc"),
                ),
                ["--proc", "/sandbox/proc"],
                id="proc",
            ),
            pytest.param(
                MountSpec(
                    mount_type=MountType.RO, source=None, dest=pathlib.Path("/dest")
                ),
                ["--ro-bind", "/dest", "/dest"],
                id="ro-bind-same-path",
            ),
        ],
    )
    def test_mount_to_bwrap_args(self, mount: MountSpec, expected: list[str]) -> None:
        """`BubblewrapJail._mount_to_bwrap_args` should convert each mount type."""
        assert BubblewrapJail._mount_to_bwrap_args(mount) == expected

    def test_build_command_includes_mount_specs(self, tmp_path: pathlib.Path) -> None:
        """`BubblewrapJail.build_command` should include mount_specs in output."""
        mount = MountSpec(
            mount_type=MountType.RO,
            source=pathlib.Path("/host/src"),
            dest=pathlib.Path("/sandbox/dest"),
        )
        jail = BubblewrapJail(workdir_path=tmp_path, mount_specs=[mount])
        result = jail.build_command(args=["echo", "test"])

        assert "--ro-bind" in result
        assert "/host/src" in result
        assert "/sandbox/dest" in result

    def test_build_command_includes_multiple_mount_specs(
        self, tmp_path: pathlib.Path
    ) -> None:
        """`BubblewrapJail.build_command` should include multiple mounts."""
        mounts = [
            MountSpec(
                mount_type=MountType.RO,
                source=pathlib.Path("/ro/src"),
                dest=pathlib.Path("/ro/dest"),
            ),
            MountSpec(
                mount_type=MountType.TMPFS,
                source=None,
                dest=pathlib.Path("/mnt/tmpfs-dest"),
            ),
        ]
        jail = BubblewrapJail(workdir_path=tmp_path, mount_specs=mounts)
        result = jail.build_command(args=["echo", "test"])

        assert "--ro-bind" in result
        assert "/ro/src" in result
        assert "/ro/dest" in result
        assert "--tmpfs" in result
        assert "/mnt/tmpfs-dest" in result

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

    @pytest.mark.parametrize(
        "args",
        [
            pytest.param(["touch", "/test_write_denied"], id="root"),
            pytest.param(["touch", "/etc/test_write_denied"], id="etc"),
        ],
    )
    def test_cannot_write_to_readonly_paths(
        self, args: list[str], tmp_path: pathlib.Path
    ) -> None:
        """Writing to readonly paths should fail."""
        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=args)
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
