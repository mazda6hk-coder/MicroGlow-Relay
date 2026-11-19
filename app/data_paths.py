"""Stable per-user data location for installed Windows builds."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import Mapping


def resolve_data_directory(
    executable_root: Path,
    explicit_directory: Path | None,
    *,
    frozen: bool,
    windows: bool,
    environment: Mapping[str, str] | None = None,
) -> Path:
    if explicit_directory is not None:
        return explicit_directory.resolve()
    if not frozen or not windows:
        return (executable_root / "data").resolve()
    env = os.environ if environment is None else environment
    local_app_data = env.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return (base / "MicroGlow Relay" / "data").resolve()


def migrate_portable_data(executable_root: Path, destination: Path) -> bool:
    """Copy legacy adjacent data once; leave the original untouched.

    A staged copy ensures that a failed copy is never mistaken for a completed
    migration on the next launch. Existing destination data always wins.
    """
    legacy = (executable_root / "data").resolve()
    destination = destination.resolve()
    if destination.exists() or not legacy.is_dir() or legacy == destination:
        return False
    if not (legacy / "microglow-relay-settings.json").is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="relay-migrate-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "data"
        shutil.copytree(legacy, staged)
        if destination.exists():
            return False
        staged.rename(destination)
    return True
