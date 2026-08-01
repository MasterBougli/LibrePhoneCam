"""Where to find bundled assets and where it is safe to write.

A PyInstaller build unpacks read-only assets into a temporary directory and may
sit in Program Files, so "next to the code" is the wrong answer for both
questions once the app is frozen.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LibrePhoneCam"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    """Root of the read-only assets (the `web/` tree)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def web_dir() -> Path:
    return bundle_dir() / "web"


def icon_path(suffix: str) -> Path | None:
    """The window icon, or None if it has not been generated yet.

    A frozen build gets it at the bundle root; running from source reads it
    straight out of build-tools, so a fresh clone still shows the real icon
    without anyone having to run the build first.
    """
    name = f"{APP_NAME}.{suffix}"
    for candidate in (
        bundle_dir() / name,
        Path(__file__).resolve().parent.parent / "build-tools" / name,
    ):
        if candidate.is_file():
            return candidate
    return None


def data_dir() -> Path:
    """Writable location for the generated certificate.

    Frozen builds land in Program Files often enough that writing beside the
    executable is not dependable; the per-user application data directory
    always is.
    """
    if not is_frozen():
        return Path(__file__).resolve().parent.parent

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
