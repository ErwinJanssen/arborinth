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

Arborinth is currently in the **design and exploration phase**.

No implementation exists yet. The repository serves as a place to document
ideas, architecture, constraints and design decisions before development
begins. Contributions, ideas and feedback are welcome!
