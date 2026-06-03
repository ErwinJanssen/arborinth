"""Test suite for Arborinth."""

INVALID_WORKSPACE_NAME_INPUTS = {
    "argnames": ("name", "exception_type", "message_substring"),
    "argvalues": [
        ("", ValueError, "cannot be empty"),
        ("test/name", ValueError, "cannot contain path separators"),
        (r"test\name", ValueError, "cannot contain path separators"),
        ("../attack", ValueError, "cannot contain path separators"),
        ("test..name", ValueError, "cannot contain '..'"),
        (".hidden", ValueError, "cannot start with '.'"),
        ("test<name", ValueError, "forbidden characters"),
        ("test>name", ValueError, "forbidden characters"),
        ("test:name", ValueError, "forbidden characters"),
        ('test"name', ValueError, "forbidden characters"),
        ("test|name", ValueError, "forbidden characters"),
        ("test?name", ValueError, "forbidden characters"),
        ("test*name", ValueError, "forbidden characters"),
        ("test name", ValueError, "whitespace"),
        ("test\tname", ValueError, "whitespace"),
        ("test\nname", ValueError, "whitespace"),
        ("test\rname", ValueError, "whitespace"),
    ],
}
