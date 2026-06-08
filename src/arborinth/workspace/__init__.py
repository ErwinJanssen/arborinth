"""Arborinth workspace module.

This module provides the core Workspace functionality for managing
isolated workspaces where untrusted code can perform its work.
"""

from .logic import Workspace

__all__ = ["Workspace"]
