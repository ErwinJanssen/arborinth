# Arborinth

Safely run untrusted code on your repository in isolated, controlled
environments.

## Overview

Arborinth is an experimental tool for safely running untrusted code against a
Git repository without granting that code unrestricted access to the host system
or the original repository state.

The project is designed around the goal that untrusted code should be able to
inspect a repository and make changes, but those changes should happen in an
isolated workspace with controlled access to secrets, repository state and the
host system.

Arborinth is intended for scenarios where code execution must be treated as
potentially unreliable or untrusted. While motivated by the rise of AI coding
agents, the scope is intentionally broader than just AI-specific tooling.

## Goals

Arborinth aims to provide:

- Reproducible and isolated execution environments for untrusted workloads.
- Controlled access to repository state.
- Writable derived workspaces without mutating the original checkout.
- Auditability of changes and execution.
- Local-first workflow.

Sandboxing and isolation build on existing technologies such as containers and
virtual machines.

## Use Cases

### AI Coding Agents

Allow an AI agent to inspect a repository, modify files, run tests, execute
linters and create commits. All in its own isolated environment, without
directly affecting the original repository or the host environment.

### Parallel Execution

Run multiple isolated executions against the same repository state concurrently.

## Why "Arborinth"?

Arborinth combines _arbor_ (Latin for tree) and _labyrinth_.

Each isolated execution environment gets its own derived tree: a writable clone
of your repository. With parallel execution, these derived trees form a forest
of isolated states growing from the shared origin.

The _labyrinth_ represents the winding, purposeful path you take through this
forest: inspecting, testing and comparing derived states in isolation. Unlike a
maze where you can get lost, a labyrinth has a single, meaningful path to its
destination. You always progress. The original tree remains untouched at the
heart of it all.

## Status

Arborinth is currently in the **early development phase**.

A basic implementation of the `project`, `workspace` and `shell` modules exists.
The `project` module can be used to inspect the Git repository root from a given
working directory, and the `workspace` module provides isolated workspaces where
untrusted code can operate safely. The `shell` module provides the ability to
run shell sessions or commands inside workspaces.

## Concepts

### Project

A project represents a top-level Arborinth entity, typically associated with a
Git repository. It serves as the central entry point for Arborinth operations.

### Workspace

A workspace is an isolated environment derived from a project's Git repository.
Each workspace contains its own clone of the repository (in the `workdir`
subdirectory) where untrusted code can perform operations without affecting the
original repository or other workspaces. It also contains a scratch directory
(in the `tmp` subdirectory), mounted at `/tmp` inside jail backends that support
mounts, which holds disposable data and can be safely deleted at any time. It
also contains a cache directory (in the `cache` subdirectory), which holds
disposable cached data, such as package manager caches.

### Shell

The shell module provides the ability to run shell sessions or commands inside
workspaces. It uses a jail abstraction to control the execution environment. The
following jail backends are available:

- `none`: runs commands directly on the host (without isolation) in the
  workspace's working directory. This is intended for convenience when you are
  certain the commands are safe.
- `bubblewrap`: runs commands in a
  [Bubblewrap](https://github.com/containers/bubblewrap) sandbox. Mounts inside
  the sandbox can be configured with mount specifications (see the `--mount`
  option below).

The `bubblewrap` backend runs the command with all namespaces unshared, except
the network, so the sandboxed process keeps network access. The entire host
filesystem is mounted read-only, and only the workspace's working directory is
mounted read-write. A process can therefore only modify files in its own working
directory: accidental changes to any other file, on the host or in other
workspaces, are impossible. At the same time, the process sees the same files,
tool configurations and tools as on the host, so the environment stays
convenient and familiar. A private `/dev` and `/proc` are provided. The
workspace's scratch directory (the `tmp` subdirectory) is mounted read-write at
`/tmp`, so scratch data persists across invocations and can be inspected from
the host. The workspace's cache directory (the `cache` subdirectory) is mounted
read-write at the user's cache directory (`XDG_CACHE_HOME`, default `~/.cache`),
so tools that cache data, such as package managers, write to the workspace
instead of failing on the read-only host cache. `/run` is masked with a fresh
tmpfs, so host sockets, such as the ssh-agent and D-Bus, are not reachable from
the sandbox. The user's runtime directory and the resolver configuration are
preserved, so tools and DNS keep working. Mounts configured with `--mount` are
applied after the defaults, in the order given, so a mount can override a
default mount for the same destination (for example, `--mount tmpfs:/tmp`
restores an ephemeral `/tmp`).

## Usage

### project command

The `project` subcommand provides operations for managing Arborinth projects.

```bash
# Display information about the current project (shows Git root)
arborinth project info

# Use a specific working directory
arborinth project info --workdir /path/to/dir
```

### workspace command

The `workspace` subcommand provides operations for managing isolated workspaces.

```bash
# Create a new workspace (clones the repository)
arborinth workspace create my_workspace

# Create a workspace in a specific project directory
arborinth workspace create my_workspace --workdir /path/to/repo

# List all workspaces for a project
arborinth workspace list

# Display information about a specific workspace
arborinth workspace info my_workspace

# Delete a workspace
arborinth workspace delete my_workspace
```

### shell command

The `shell` subcommand provides operations for running shell sessions or
commands in workspaces.

```bash
# Open a shell session in a workspace
arborinth shell my_workspace

# Run a command in a workspace
arborinth shell my_workspace echo "Hello, World!"

# Run a command with flags in a workspace (note the `--` separator)
arborinth shell my_workspace -- git branch --all

# Run a command in a Bubblewrap sandbox
arborinth shell my_workspace --jail bubblewrap echo "Hello, World!"

# Run a command with mounts inside the sandbox
arborinth shell my_workspace --jail bubblewrap --mount rw:/home/user/data:/data -- git branch --all
```

Mount specifications given to `--mount` have the form `TYPE:dest` or
`TYPE:source:dest`, where `TYPE` is one of:

- `ro`: read-only bind mount
- `rw`: read-write bind mount
- `tmpfs`: in-memory filesystem mount
- `dev`: device filesystem mount (usually `/dev`)
- `proc`: procfs mount (usually `/proc`)

For `ro` and `rw`, the source path can be omitted, in which case the destination
path is used as the source. The `tmpfs`, `dev` and `proc` types only take a
destination path.

### Python API

Both `Project` and `Workspace` classes can be used programmatically:

```python
from arborinth import Project
from arborinth.shell import JailBackend, MountSpec

# Create a project with the current working directory
project = Project()

# Get the Git repository root
root = project.repo_root_path
print(f"Repository root: {root}")

# Create a workspace
workspace = project.create_workspace("my_workspace")

# Access workspace paths
print(f"Workspace root: {workspace.root_path}")
print(f"Workspace workdir: {workspace.workdir_path}")

# List existing workspaces
workspaces = project.workspaces

# Retrieve a specific workspace
ws = project.workspace("my_workspace")

# Run a shell or command in a workspace
result = ws.shell(args=["echo", "hello"], jail_backend=JailBackend.NONE)
print(f"Exit code: {result.returncode}")

# Run a command in a Bubblewrap sandbox
result = ws.shell(args=["git", "branch"], jail_backend=JailBackend.BUBBLEWRAP)

# Run a command with additional mounts in the sandbox
mounts = [MountSpec.from_spec("rw:/home/user/data:/data")]
result = ws.shell(
    args=["git", "branch"],
    jail_backend=JailBackend.BUBBLEWRAP,
    mount_specs=mounts,
)

# Delete a workspace
ws.delete()
```

The `Project` class validates that the working directory exists and is within a
Git repository. Workspace names are validated to prevent path traversal attacks
and other security issues. The `shell` method uses a jail backend to control the
execution environment.

## Development

Contributions, ideas and feedback are welcome!
