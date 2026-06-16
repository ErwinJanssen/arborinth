# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
