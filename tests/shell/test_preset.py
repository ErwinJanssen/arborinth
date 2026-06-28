"""Tests for the preset module."""

from __future__ import annotations

import pathlib

import pytest

from arborinth.shell import MountSpec, MountType, get_preset, list_presets
from arborinth.shell.preset import BUILTIN_PRESETS, Preset


class TestPreset:
    """Tests for the ``Preset`` dataclass."""

    def test_preset_holds_name(self) -> None:
        """A ``Preset`` should store its name."""
        p = Preset(name="test")
        assert p.name == "test"

    def test_preset_holds_default_command(self) -> None:
        """A ``Preset`` should store its default command."""
        p = Preset(name="test", default_command="echo hello")
        assert p.default_command == "echo hello"

    def test_preset_default_command_is_optional(self) -> None:
        """A ``Preset`` should allow ``None`` as default command."""
        p = Preset(name="test")
        assert p.default_command is None

    def test_preset_holds_mount_specs(self) -> None:
        """A ``Preset`` should store its mount specs."""
        m = MountSpec(
            mount_type=MountType.TMPFS,
            source=None,
            dest=pathlib.Path("/tmp"),  # noqa: S108
        )
        p = Preset(name="test", mount_specs=(m,))
        assert len(p.mount_specs) == 1
        assert p.mount_specs[0] == m

    def test_preset_mount_specs_defaults_to_empty(self) -> None:
        """A ``Preset`` should default to an empty mount spec tuple."""
        p = Preset(name="test")
        assert p.mount_specs == ()

    def test_preset_is_frozen(self) -> None:
        """A ``Preset`` should be immutable."""
        p = Preset(name="test")
        with_patch = p.mount_specs  # noqa: F841
        try:
            p.name = "changed"  # type: ignore[misc]
            pytest.fail("Should have raised")
        except AttributeError:
            pass

    def test_preset_is_hashable(self) -> None:
        """A ``Preset`` should be usable in a set or as dict key."""
        p = Preset(name="test")
        _ = {p: 1}


class TestPresetRegistry:
    """Tests for the built-in preset registry."""

    def test_list_presets_returns_sorted_names(self) -> None:
        """``list_presets()`` should return sorted preset names."""
        names = list_presets()
        assert names == sorted(names)
        assert "opencode" in names

    def test_get_preset_returns_preset(self) -> None:
        """``get_preset()`` should return the matching ``Preset``."""
        p = get_preset("opencode")
        assert isinstance(p, Preset)
        assert p.name == "opencode"

    def test_get_preset_default_command(self) -> None:
        """The ``opencode`` preset should have a default command."""
        p = get_preset("opencode")
        assert p.default_command == "opencode"

    def test_get_preset_has_mount_specs(self) -> None:
        """The ``opencode`` preset should define mount specs."""
        p = get_preset("opencode")
        assert len(p.mount_specs) > 0

    def test_get_preset_has_config_mount(self) -> None:
        """The ``opencode`` preset should mount config as read-only."""
        p = get_preset("opencode")
        home = pathlib.Path.home()
        config_mount = MountSpec(
            mount_type=MountType.RO,
            source=home / ".config" / "opencode",
            dest=home / ".config" / "opencode",
        )
        assert config_mount in p.mount_specs

    def test_get_preset_has_cache_mount(self) -> None:
        """The ``opencode`` preset should mount cache as read-write."""
        p = get_preset("opencode")
        home = pathlib.Path.home()
        cache_mount = MountSpec(
            mount_type=MountType.RW,
            source=home / ".cache" / "opencode",
            dest=home / ".cache" / "opencode",
        )
        assert cache_mount in p.mount_specs

    def test_get_preset_has_data_mount(self) -> None:
        """The ``opencode`` preset should mount local share data as read-write."""
        p = get_preset("opencode")
        home = pathlib.Path.home()
        data_mount = MountSpec(
            mount_type=MountType.RW,
            source=home / ".local" / "share" / "opencode",
            dest=home / ".local" / "share" / "opencode",
        )
        assert data_mount in p.mount_specs

    def test_get_preset_has_state_mount(self) -> None:
        """The ``opencode`` preset should mount local state as read-write."""
        p = get_preset("opencode")
        home = pathlib.Path.home()
        state_mount = MountSpec(
            mount_type=MountType.RW,
            source=home / ".local" / "state" / "opencode",
            dest=home / ".local" / "state" / "opencode",
        )
        assert state_mount in p.mount_specs

    def test_get_unknown_preset_raises(self) -> None:
        """``get_preset()`` should raise ``KeyError`` for unknown presets."""
        try:
            get_preset("nonexistent")
            pytest.fail("Should have raised KeyError")
        except KeyError:
            pass

    def test_get_unknown_preset_error_message(self) -> None:
        """The error message should list available presets."""
        try:
            get_preset("bogus")
        except KeyError as exc:
            msg = str(exc)
            assert "bogus" in msg
            assert "opencode" in msg

    def test_builtin_presets_are_consistent(self) -> None:
        """Every entry in ``BUILTIN_PRESETS`` should pass basic sanity checks."""
        for name, preset in BUILTIN_PRESETS.items():
            assert preset.name == name
            assert isinstance(preset.mount_specs, tuple)
            for m in preset.mount_specs:
                assert isinstance(m, MountSpec)
