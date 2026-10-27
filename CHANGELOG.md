# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Workspaces now have a scratch directory (the `tmp` subdirectory, next to
  `workdir`), exposed as `Workspace.tmp_path`. It is created on demand when a
  shell is run and can be safely deleted at any time.
- Workspaces now have a cache directory (the `cache` subdirectory, next to
  `workdir`), exposed as `Workspace.cache_path`. Like the scratch directory, it
  is created on demand when a shell is run and can be safely deleted at any
  time.

### Changed

- The clone's `origin` remote now points at the original repository with a
  relative path, so that workspaces keep working when the repository directory
  is moved.
- The `bubblewrap` jail backend now binds the workspace's scratch directory at
  `/tmp`, instead of a fresh tmpfs. Scratch data now persists across invocations
  and can be inspected from the host. An ephemeral `/tmp` can still be requested
  with `--mount tmpfs:/tmp`.
- The `bubblewrap` jail backend now binds the workspace's cache directory at the
  user's cache directory (`XDG_CACHE_HOME`, defaulting to `~/.cache`) inside the
  sandbox. Tools that cache data, such as package managers, now write to the
  workspace instead of failing on the read-only host cache.

## v0.2.0 - 2026-10-18

This release adds the `bubblewrap` jail backend, providing increased isolation
for commands run in workspaces.

### Added

- `bubblewrap` jail backend for running commands in a sandboxed environment
  using Bubblewrap. This can be selected with the `--jail=bubblewrap` CLI
  option.
- `MountSpec` and `MountType` classes for configuring mounts in jail backends.
- `shell --mount` CLI option to configure mounts.

### Known Limitations

- The `bubblewrap` backend is a thin layer of filesystem isolation: a sandboxed
  process can only modify files in its workspace's working directory, while
  still being able to read any file on the host and reach the network. It
  protects against accidental modification, not against malicious processes.

## v0.1.0 - 2026-06-16

This is the initial release of Arborinth. It provides basic functionality for
Git repository introspection, workspace creation, and running commands in
workspaces. The project is still in its early stages and may contain bugs or
limitations. Please report any issues you encounter.

### Added

- Initial release of Arborinth.
- `project` module for Git repository introspection.
- `workspace` module for creating isolated repository clones.
- `shell` module for running commands in workspaces.
- CLI commands: `arborinth project`, `arborinth workspace`, `arborinth shell`.

### Known Limitations

- The `shell` module currently only supports `NoneJail` backend which provides
  **no isolation**, commands run directly on the host in the workspace
  directory. This is intended for convenience when you are certain the commands
  are safe. Actual jailing (via firejail, bubblewrap, etc.) is planned for
  future releases.
