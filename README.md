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

- Reproducable and isolated execution environments for untrusted workloads.
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
directly affecting the original respository or the host environment.

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

A basic implementation of the `project` and `workspace` modules exists. The
`project` module can be used to inspect the Git repository root from a given
working directory, and the `workspace` module provides isolated workspaces where
untrusted code can operate safely.

## Concepts

### Project

A project represents a top-level Arborinth entity, typically associated with
a Git repository. It serves as the central entry point for Arborinth operations.

### Workspace

A workspace is an isolated environment derived from a project's Git repository.
Each workspace contains its own clone of the repository (in the `workdir`
subdirectory) where untrusted code can perform operations without affecting the
original repository or other workspaces.

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

### Python API

Both `Project` and `Workspace` classes can be used programmatically:

```python
from arborinth import Project

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

# Delete a workspace
ws.delete()
```

The `Project` class validates that the working directory exists and is within a
Git repository. Workspace names are validated to prevent path traversal attacks
and other security issues.

## Development

Contributions, ideas and feedback are welcome!
