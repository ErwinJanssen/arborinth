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

A basic implementation of the `Project` module exists and can be used to inspect
the Git repository root from a given working directory.

## Usage

### Project Command

The `project` subcommand provides operations for managing Arborinth projects.

```bash
# Display information about the current project (shows Git root)
arborinth project info

# Use a specific working directory
arborinth project info --workdir /path/to/dir
```

### Project Module (Python API)

The `Project` class can be used programmatically:

```python
from arborinth import Project

# Create a project with the current working directory
project = Project()

# Get the Git repository root
root = project.repo_root_path
print(f"Repository root: {root}")

# Specify a different working directory
project = Project(workdir="/path/to/dir")
root = project.repo_root_path
```

The `Project` class validates that the working directory exists and is within
a Git repository.

## Development

Contributions, ideas and feedback are welcome!
