"""Tests for the Arborinth utility functions."""

import json

import pytest

from arborinth import _util


class TestInfoFormat:
    """Tests for the InfoFormat enum."""

    def test_info_format_text_value(self) -> None:
        """InfoFormat.TEXT should have value 'text'."""
        assert _util.InfoFormat.TEXT.value == "text"

    def test_info_format_json_value(self) -> None:
        """InfoFormat.JSON should have value 'json'."""
        assert _util.InfoFormat.JSON.value == "json"


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

    def test_format_info_json_format(self) -> None:
        """format_info with JSON format should return JSON string."""
        info = {"key": "value", "another_key": "another_value"}
        result = _util.format_info(info, _util.InfoFormat.JSON)
        parsed = json.loads(result)
        assert parsed == info

    def test_format_info_json_empty_dict(self) -> None:
        """format_info with JSON format and empty dict should return '{}'."""
        result = _util.format_info({}, _util.InfoFormat.JSON)
        assert result == "{}"

    def test_format_info_json_with_underscores(self) -> None:
        """format_info with JSON format should preserve underscore keys."""
        info = {"my_key": "value"}
        result = _util.format_info(info, _util.InfoFormat.JSON)
        parsed = json.loads(result)
        assert parsed == {"my_key": "value"}

    def test_format_info_unknown_format_raises(self) -> None:
        """format_info with unknown format should raise ValueError."""

        # Create a mock enum value that's not TEXT or JSON
        class MockFormat:
            pass

        mock_format = MockFormat()
        with pytest.raises(ValueError, match="Unknown format"):
            _util.format_info({"key": "value"}, mock_format)
