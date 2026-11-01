# Arborinth

## Development

- The project uses [uv](https://docs.astral.sh/uv/). Run commands through it,
  e.g. `uv run pytest` or `uv run arborinth ...`. Dependencies are managed with
  uv (`uv add`, `uv lock`); `uv.lock` is committed.

## Verification

- The full test suite is `pytest`. Tests run real `git`; the integration tests
  also run a nested `bubblewrap` and skip automatically when it is unavailable.
- Pre-commit hooks run `ruff check`, `ruff format`, `mdformat` and
  `docformatter`. Formatting authority lives in the hooks: when a hook rewrites
  a file, keep its output.
- Markdown and docstrings wrap at 80 characters, configured in `pyproject.toml`.

## Changelog

- Every behavior change updates the `Unreleased` section of `CHANGELOG.md` in
  the same commit. Release commits bump `pyproject.toml` and `uv.lock` together,
  date the section, and regroup the notes into thematic sections.

## Tests

- Prefer real `git` over mocks: real clones, real remotes, and commit identity
  through repo-local configuration (`git config --local`), so tests never depend
  on the host's global Git configuration.
- Integration tests probe the actual environment (host `PATH`,
  `XDG_RUNTIME_DIR`, a host socket file) and `pytest.skip` when a probe is
  unavailable, instead of assuming the host's layout.
