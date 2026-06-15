"""Logic for the Arborinth's 'workspace' concept.

This module contains the core `Workspace` class which represents an isolated
workspace derived from a Git repository. Workspaces are clones of the original
repository where untrusted code can make changes without affecting the original
repository.
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import typing

from arborinth import _util

if typing.TYPE_CHECKING:
    import pathlib

    from arborinth import Project


@dataclasses.dataclass
class Workspace:
    """An isolated workspace for untrusted code execution.

    A workspace contains a clone of a Git repository (in the `workdir`
    subdirectory) where untrusted code can perform operations without affecting
    the original repository.

    Attributes:
        name: The name of the workspace.
        project: The Arborinth `Project` associated with the original repository.
    """

    name: str
    project: Project

    def __post_init__(self) -> None:
        """Validate the workspace after initialization.

        Raises:
            ValueError: If the workspace name is invalid.
            FileNotFoundError: If the workspace directory does not exist.
        """
        _util.validate_workspace_name(self.name)

        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)

    @property
    def root_path(self) -> pathlib.Path:
        """Path to this specific workspace directory.

        Returns:
            The absolute path to the workspace directory.
        """
        return self.project.workspace_root_path / self.name

    @property
    def workdir_path(self) -> pathlib.Path:
        """Path to the workdir (Git repository clone) within this workspace.

        Returns:
            The absolute path to the workspace's workdir directory, which
            contains the cloned Git repository.
        """
        return self.root_path / "workdir"

    @property
    def remote_name(self) -> str:
        """Name of the remote in the original repository.

        Returns:
            The namespaced remote name: `arborinth/<workspace_name>`.
        """
        return f"arborinth/{self.name}"

    @property
    def info(self) -> dict[str, str]:
        """Workspace information as a dictionary.

        Returns:
            A dictionary containing workspace name, path, and remote name.
        """
        return {
            "workspace_name": self.name,
            "path": str(self.root_path),
            "remote": self.remote_name,
        }

    def register_as_remote(self) -> None:
        """Register this workspace as a remote in the original repository.

        Adds a git remote named `arborinth/<workspace_name>` pointing to the
        workspace's clone directory in the original repository.

        Raises:
            RuntimeError: If registering the remote fails.
        """
        try:
            subprocess.run(
                [
                    "git",
                    "remote",
                    "add",
                    self.remote_name,
                    str(self.workdir_path),
                ],
                cwd=self.project.repo_root_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            message = (
                f"Failed to register remote '{self.remote_name}' in original repository: "  # noqa: E501
                f"{exc.stderr.strip() if exc.stderr else 'unknown error'}"
            )
            raise RuntimeError(message) from exc
        except FileNotFoundError as exc:
            message = (
                f"Cannot register remote '{self.remote_name}': "
                f"Git is not installed or not found in PATH."
            )
            raise RuntimeError(message) from exc

    def unregister_as_remote(self) -> None:
        """Unregister this workspace's remote from the original repository.

        Removes the git remote named `arborinth/<workspace_name>` from the
        original repository.

        Silently ignores errors if the remote doesn't exist or git is
        unavailable.
        """
        try:
            subprocess.run(
                [
                    "git",
                    "remote",
                    "remove",
                    self.remote_name,
                ],
                cwd=self.project.repo_root_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # Ignore errors if the remote doesn't exist
            pass
        except FileNotFoundError:
            # Ignore if git is not available
            pass

    def delete(self) -> None:
        """Delete this workspace.

        Removes the workspace directory from the filesystem, including all its
        contents. Also removes the corresponding remote from the original
        repository if it exists.

        Raises:
            FileNotFoundError: If the workspace directory does not exist.
            OSError: If the directory cannot be removed.
        """
        if not self.root_path.is_dir():
            message = f"Workspace '{self.name}' does not exist at {self.root_path}"
            raise FileNotFoundError(message)

        self.unregister_as_remote()

        shutil.rmtree(self.root_path)

    def shell(
        self, args: typing.Sequence[str] | None = None
    ) -> subprocess.CompletedProcess:
        """Run a shell or command in this workspace.

        Opens a shell session in the workspace's workdir. If args is `None`, the
        default shell is used.

        For the default shell, `$SHELL` environment variable is attempted first
        with fallbacks to `bash` and `sh` (in that order). The shell binary must
        be found in the system `$PATH`.

        The command is executed in the workspace's workdir directory, which
        contains the cloned Git repository. The process's stdout and stderr are
        not captured, allowing for interactive use.

        Args:
            args: The command and arguments to run. If `None`, runs the default
                shell.

        Returns:
            A `subprocess.CompletedProcess` object containing the process
            metadata, including the return code.

        Raises:
            FileNotFoundError: If the shell or command is not found in `$PATH`.
        """
        if args is None:
            shell = os.environ.get("SHELL")

            # If no default `$SHELL` is set, or if the shell binary is not
            # found, attempt to use `bash` or `sh` as a fallback.
            if not shell or shutil.which(shell) is None:
                shell = shutil.which("bash") or shutil.which("sh")

            # If there is no shell available (both `$SHELL` and fallbacks are
            # missing), raise an error.
            if not shell:
                message = "No shell binary available."
                raise FileNotFoundError(message)

            # Use the shell as the command to run.
            args = [shell]

        # Might raise `FileNotFoundError` if the command is not found.
        return subprocess.run(
            args,
            # Run the command in the workspace's workdir.
            cwd=self.workdir_path,
            # Do not raise an exception if the command fails in order to
            # propagate the exit code.
            check=False,
            # Do not capture the output because the shell should be interactive.
            capture_output=False,
        )
