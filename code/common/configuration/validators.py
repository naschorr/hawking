import os
import stat
from pathlib import Path

from common import utilities


def resolve_config_path(file_path: Path | str) -> Path:
    """Resolve a file path, relative to the application root or absolutely."""

    path = Path(file_path)
    if path.is_absolute():
        return path
    return utilities.get_root_path() / path


def validate_directory_exists(directory_path: Path | str) -> Path:
    """Return a directory path only if it already exists as a directory."""

    path = Path(directory_path)
    if not path.exists():
        raise ValueError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    return path


def validate_directory_path(directory_path: Path | str) -> Path:
    """Accept a not-yet-created output directory, but reject existing non-directories."""

    path = Path(directory_path)
    if path.exists() and not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    return path


def validate_file_exists(file_path: Path | str) -> Path:
    """Return a file path only if it already exists as a file."""

    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"File does not exist or is not a file: {path}")
    return path


def is_file_accessible(file_path: Path | str) -> bool:
    """
    Ensure a configured file exists and is readable/writable.

    Creates missing files and parent directories, and attempts to correct
    permissions on existing files.
    """

    path = Path(file_path)
    try:
        if path.is_file():
            if os.access(path, os.R_OK) and os.access(path, os.W_OK):
                return True
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
            return os.access(path, os.R_OK) and os.access(path, os.W_OK)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o644, exist_ok=True)
        return path.is_file() and os.access(path, os.R_OK) and os.access(path, os.W_OK)
    except OSError:
        return False