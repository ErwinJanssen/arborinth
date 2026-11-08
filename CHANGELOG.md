# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Shell

- `Workspace.shell`, `Jail.run` and the `arborinth shell` command accept extra
  environment variables (`env=` in Python, `--env KEY=VALUE` on the CLI), merged
  over the current environment, so a single run can be configured without
  changing any files.
- `Workspace.shell` and `Jail.run` accept `capture_output=True`, which captures
  the process's stdout and stderr as text on the returned
  `subprocess.CompletedProcess`, for unattended runs. The default is unchanged:
  output is streamed for interactive use.

### Workspaces

- `Workspace.delete` now also removes read-only directories. A process run
  inside a workspace can create them, for example a tool that marks the files it
  installs immutable, and removing them with a plain `shutil.rmtree` fails with
  `Permission denied`. On a permission error, `delete` restores the owner write
  permission on the affected directory and retries the removal.

## v0.3.0 - 2026-11-02

This release hardens the `bubblewrap` jail backend, gives workspaces their own
scratch, cache and home directories, and makes the link between a repository and
its workspaces survive repository moves.

### Workspaces

- Workspaces now have a scratch directory (the `tmp` subdirectory, next to
  `workdir`), exposed as `Workspace.tmp_path`. It is created on demand when a
  shell is run and can be safely deleted at any time.
- Workspaces now have a cache directory (the `cache` subdirectory, next to
  `workdir`), exposed as `Workspace.cache_path`. Like the scratch directory, it
  is created on demand when a shell is run and can be safely deleted at any
  time.
- Workspaces now have a home directory (the `home` subdirectory, next to
  `workdir`), exposed as `Workspace.home_path`. Like the other workspace
  directories, it is created on demand when a shell is run. Unlike the scratch
  and cache directories, its contents are not disposable by definition: the
  sandboxed process may store state in it, such as credentials. Deleting it does
  not break anything, but discards that state.
- Workspace clones are seeded with the commit identity (`user.name` and
  `user.email`) of the original repository, so that commits can be created
  inside workspaces without the host's Git configuration.

### `bubblewrap` jail backend

- The user's home directory is masked: the workspace's home directory is mounted
  read-write in its place, so files in the host home directory, such as SSH keys
  and configuration, are not reachable from the sandbox. For each `PATH` entry
  under the user's home directory, the parent directory of the entry is mounted
  read-only, so tools installed under it keep working. The workspace's cache
  directory is mounted inside the workspace home directory.
- `/run` is masked with a fresh tmpfs, so host sockets, such as the ssh-agent
  and D-Bus, are no longer reachable from the sandbox. The user's runtime
  directory and the resolver configuration are preserved, so tools and DNS keep
  working.
- The workspace's scratch directory is mounted at `/tmp`, instead of a fresh
  tmpfs. Scratch data now persists across invocations and can be inspected from
  the host. An ephemeral `/tmp` can still be requested with
  `--mount tmpfs:/tmp`.
- The workspace's cache directory is mounted at the user's cache directory
  (`XDG_CACHE_HOME`, defaulting to `~/.cache`) inside the sandbox. Tools that
  cache data, such as package managers, now write to the workspace instead of
  failing on the read-only host cache.

### Repository integration

- The clone's `origin` remote now points at the original repository with a
  relative path, so that workspaces keep working when the repository directory
  is moved.
- The `arborinth/<workspace_name>` remote in the original repository now uses a
  relative path to the workspace clone as well, so that fetching from a
  workspace keeps working when the repository directory is moved.
- The `Project` class resolves the Git repository root once, when it is created,
  instead of running `git rev-parse` on every access. Creating a `Project` now
  fails immediately if the working directory is not inside a Git repository.

### Known Limitations

- The network is still shared with the host, and the sandboxed process can read
  the rest of the host filesystem. The jail protects against accidental
  modification, not against a malicious process exfiltrating data.
- Tools that need files under the home directory beyond the parent directory of
  their `PATH` entry may not work inside the sandbox; they can be exposed
  explicitly with `--mount`.
- Running `git clean` in the original repository removes the workspace scratch,
  cache and home directories. They are recreated on demand, but home state, such
  as credentials stored in it, is lost.

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
