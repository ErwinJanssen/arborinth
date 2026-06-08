"""Tests for the Arborinth utility functions."""

from arborinth import _util


class TestFormatInfo:
    """Tests for the format_info function."""

    def test_format_info_empty_dict(self) -> None:
        """format_info with empty dict should return empty string."""
        result = _util.format_info({})
        assert result == ""

    def test_format_info_single_item(self) -> None:
        """format_info with single item should format correctly."""
        result = _util.format_info({"key": "value"})
        assert result == "key: value"

    def test_format_info_multiple_items(self) -> None:
        """format_info with multiple items should join with newlines."""
        result = _util.format_info({"key1": "value1", "key2": "value2"})
        assert result == "key1: value1\nkey2: value2"

    def test_format_info_underscore_replacement(self) -> None:
        """format_info should replace underscores with spaces."""
        result = _util.format_info({"my_key": "value"})
        assert result == "my key: value"

    def test_format_info_multiple_underscores(self) -> None:
        """format_info should replace multiple underscores."""
        result = _util.format_info({"my_long_key": "value"})
        assert result == "my long key: value"

    def test_format_info_order_preserved(self) -> None:
        """format_info should preserve dictionary insertion order."""
        # Python 3.7+ preserves dict insertion order
        result = _util.format_info({"first": "1", "second": "2", "third": "3"})
        lines = result.split("\n")
        assert lines == ["first: 1", "second: 2", "third: 3"]
