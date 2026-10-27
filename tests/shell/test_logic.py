"""Tests for the shell logic module."""

from __future__ import annotations

import os
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

    def test_build_command_masks_run(self, tmp_path: pathlib.Path) -> None:
        """`build_command` should mask `/run` with a fresh tmpfs."""
        jail = BubblewrapJail(workdir_path=tmp_path)

        result = jail.build_command(args=["echo", "test"])

        run_mask = ["--tmpfs", "/run"]
        assert any(result[i : i + 2] == run_mask for i in range(len(result) - 1))

    @pytest.mark.parametrize(
        "runtime_dir",
        [
            pytest.param("/run/user/1000", id="under-run"),
            pytest.param("/tmp/runtime", id="outside-run"),  # noqa: S108
            pytest.param(None, id="unset"),
        ],
    )
    def test_build_command_runtime_dir(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        runtime_dir: str | None,
    ) -> None:
        """A runtime dir under `/run` should be masked with its own tmpfs."""
        if runtime_dir is None:
            monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        else:
            monkeypatch.setenv("XDG_RUNTIME_DIR", runtime_dir)
        jail = BubblewrapJail(workdir_path=tmp_path)

        result = jail.build_command(args=["echo", "test"])

        # A runtime dir under `/run` is hidden by the mask, so it gets an
        # empty tmpfs of its own. A runtime dir outside `/run` is unaffected.
        masked = runtime_dir is not None and pathlib.Path(runtime_dir).is_relative_to(
            "/run"
        )
        has_runtime_mask = runtime_dir is not None and any(
            result[i : i + 2] == ["--tmpfs", runtime_dir]
            for i in range(len(result) - 1)
        )
        assert has_runtime_mask == masked

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

    def test_build_command_with_tmp_path_binds_scratch(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A configured tmp_path should be bound at `/tmp` instead of a tmpfs."""
        scratch = tmp_path / "scratch"
        jail = BubblewrapJail(workdir_path=tmp_path, tmp_path=scratch)

        result = jail.build_command(args=["echo", "test"])

        # `/tmp` is a bind mount, not a tmpfs
        assert not any(
            result[i : i + 2] == ["--tmpfs", "/tmp"]  # noqa: S108
            for i in range(len(result) - 1)
        )
        scratch_bind = ["--bind", str(scratch), "/tmp"]  # noqa: S108
        assert any(result[i : i + 3] == scratch_bind for i in range(len(result) - 2))

    def test_build_command_tmp_mount_precedes_workdir_bind(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The `/tmp` mount should be applied before the workdir bind.

        If the workdir is located under `/tmp` on the host, a later `/tmp` mount
        would shadow the workdir bind.
        """
        scratch = tmp_path / "scratch"
        jail = BubblewrapJail(workdir_path=tmp_path, tmp_path=scratch)

        result = list(jail.build_command(args=["echo", "test"]))

        workdir_str = str(tmp_path.resolve())
        scratch_bind = ["--bind", str(scratch), "/tmp"]  # noqa: S108
        workdir_bind = ["--bind", workdir_str, workdir_str]

        def bind_index(bind: list[str]) -> int:
            """Return the position of a three-element bind in the command."""
            return next(i for i in range(len(result) - 2) if result[i : i + 3] == bind)

        assert bind_index(scratch_bind) < bind_index(workdir_bind)

    def test_build_command_with_cache_path_binds_cache(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A configured cache_path should be bound at the user's cache dir."""
        cache = tmp_path / "cache"
        jail = BubblewrapJail(workdir_path=tmp_path, cache_path=cache)

        result = jail.build_command(args=["echo", "test"])

        cache_dest = os.environ.get("XDG_CACHE_HOME") or str(
            pathlib.Path.home() / ".cache"
        )
        cache_bind = ["--bind", str(cache), cache_dest]
        assert any(result[i : i + 3] == cache_bind for i in range(len(result) - 2))

    def test_build_command_cache_mount_precedes_workdir_bind(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The cache mount should be applied before the workdir bind.

        Like the `/tmp` mount, a later mount could shadow the workdir bind if
        the workdir is located under the cache directory.
        """
        cache = tmp_path / "cache"
        jail = BubblewrapJail(workdir_path=tmp_path, cache_path=cache)

        result = list(jail.build_command(args=["echo", "test"]))

        workdir_str = str(tmp_path.resolve())
        cache_dest = os.environ.get("XDG_CACHE_HOME") or str(
            pathlib.Path.home() / ".cache"
        )
        cache_bind = ["--bind", str(cache), cache_dest]
        workdir_bind = ["--bind", workdir_str, workdir_str]

        def bind_index(bind: list[str]) -> int:
            """Return the position of a three-element bind in the command."""
            return next(i for i in range(len(result) - 2) if result[i : i + 3] == bind)

        assert bind_index(cache_bind) < bind_index(workdir_bind)


class TestRunMaskArgs:
    """Tests for the `_run_mask_args` static method."""

    def test_masks_run(self, tmp_path: pathlib.Path) -> None:
        """The masked directory should be replaced by a tmpfs."""
        run = tmp_path / "run"
        result = BubblewrapJail._run_mask_args(run, tmp_path / "resolv.conf")

        assert result[:2] == ["--tmpfs", str(run)]

    def test_runtime_dir_under_run_masked(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A runtime dir under the masked dir should get its own tmpfs."""
        run = tmp_path / "run"
        runtime_dir = run / "user" / "1000"
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        result = BubblewrapJail._run_mask_args(run, tmp_path / "resolv.conf")

        assert result[2:4] == ["--tmpfs", str(runtime_dir)]

    def test_runtime_dir_outside_run_not_masked(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A runtime dir outside the masked dir should not get a tmpfs."""
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

        result = BubblewrapJail._run_mask_args(
            tmp_path / "run", tmp_path / "resolv.conf"
        )

        assert result[2:] == []

    def test_resolv_conf_symlink_into_run_bound(self, tmp_path: pathlib.Path) -> None:
        """A resolv.conf symlink into the masked dir should get a bind."""
        run = tmp_path / "run"
        resolve_dir = run / "systemd" / "resolve"
        resolve_dir.mkdir(parents=True)
        target = resolve_dir / "stub-resolv.conf"
        target.touch()
        resolv_conf = tmp_path / "resolv.conf"
        resolv_conf.symlink_to(target)

        result = BubblewrapJail._run_mask_args(run, resolv_conf)

        assert result[-3:] == ["--ro-bind", str(target), str(target)]

    def test_resolv_conf_regular_file_not_bound(self, tmp_path: pathlib.Path) -> None:
        """A regular resolv.conf file is visible through the root bind."""
        resolv_conf = tmp_path / "resolv.conf"
        resolv_conf.touch()

        result = BubblewrapJail._run_mask_args(tmp_path / "run", resolv_conf)

        assert "--ro-bind" not in result

    def test_resolv_conf_symlink_outside_run_not_bound(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A resolv.conf symlink outside the masked dir needs no bind."""
        other = tmp_path / "other"
        other.mkdir()
        (other / "resolv.conf").touch()
        resolv_conf = tmp_path / "resolv.conf"
        resolv_conf.symlink_to(other / "resolv.conf")

        result = BubblewrapJail._run_mask_args(tmp_path / "run", resolv_conf)

        assert "--ro-bind" not in result

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

    def test_can_write_to_tmp_path(self, tmp_path: pathlib.Path) -> None:
        """With a tmp_path configured, `/tmp` should be that directory."""
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        jail = BubblewrapJail(workdir_path=tmp_path, tmp_path=scratch)

        result = jail.run(args=["touch", "/tmp/probe"])  # noqa: S108

        assert result.returncode == 0
        assert (scratch / "probe").exists()

    def test_tmp_path_persists_across_runs(self, tmp_path: pathlib.Path) -> None:
        """Scratch data in tmp_path should persist across jail invocations."""
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        jail = BubblewrapJail(workdir_path=tmp_path, tmp_path=scratch)

        write_result = jail.run(args=["touch", "/tmp/probe"])  # noqa: S108
        read_result = jail.run(args=["test", "-e", "/tmp/probe"])  # noqa: S108

        assert write_result.returncode == 0
        assert read_result.returncode == 0

    def test_can_write_to_cache_path(self, tmp_path: pathlib.Path) -> None:
        """With a cache_path configured, the user cache dir should be it."""
        cache = tmp_path / "cache"
        cache.mkdir()
        jail = BubblewrapJail(workdir_path=tmp_path, cache_path=cache)

        cache_dest = os.environ.get("XDG_CACHE_HOME") or str(
            pathlib.Path.home() / ".cache"
        )
        result = jail.run(args=["touch", f"{cache_dest}/probe"])

        assert result.returncode == 0
        assert (cache / "probe").exists()

    def test_cache_path_persists_across_runs(self, tmp_path: pathlib.Path) -> None:
        """Cached data in cache_path should persist across jail invocations."""
        cache = tmp_path / "cache"
        cache.mkdir()
        jail = BubblewrapJail(workdir_path=tmp_path, cache_path=cache)

        cache_dest = os.environ.get("XDG_CACHE_HOME") or str(
            pathlib.Path.home() / ".cache"
        )
        write_result = jail.run(args=["touch", f"{cache_dest}/probe"])
        read_result = jail.run(args=["test", "-e", f"{cache_dest}/probe"])

        assert write_result.returncode == 0
        assert read_result.returncode == 0

    def test_run_host_socket_not_reachable(self, tmp_path: pathlib.Path) -> None:
        """Host socket files in `/run` should not exist in the sandbox."""
        ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK")
        if not ssh_auth_sock or not pathlib.Path(ssh_auth_sock).is_relative_to("/run"):
            pytest.skip("no host socket file under /run")

        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["test", "-e", ssh_auth_sock])
        assert result.returncode != 0

    def test_run_resolv_conf_readable(self, tmp_path: pathlib.Path) -> None:
        """The resolver configuration should stay readable with `/run` masked."""
        if not pathlib.Path("/etc/resolv.conf").exists():
            pytest.skip("no resolver configuration")

        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["cat", "/etc/resolv.conf"])
        assert result.returncode == 0

    def test_run_runtime_dir_exists_when_configured(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The runtime dir should exist in the sandbox when it is set."""
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if not runtime_dir or not pathlib.Path(runtime_dir).is_relative_to("/run"):
            pytest.skip("no runtime dir under /run")

        jail = BubblewrapJail(workdir_path=tmp_path)
        result = jail.run(args=["test", "-d", runtime_dir])
        assert result.returncode == 0

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
