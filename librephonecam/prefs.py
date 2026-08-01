"""Remembered language and theme for the desktop window."""

from __future__ import annotations

import json
from typing import Any

from . import i18n
from .paths import data_dir

FILE = "settings.json"


def load() -> dict[str, Any]:
    path = data_dir() / FILE
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        stored = {}
    if not isinstance(stored, dict):
        stored = {}

    lang = stored.get("lang")
    theme = stored.get("theme")
    return {
        "lang": lang if lang in i18n.LANGUAGES else i18n.detect(),
        "theme": theme if theme in ("dark", "light") else "dark",
    }


def save(lang: str, theme: str) -> None:
    path = data_dir() / FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"lang": lang, "theme": theme}), encoding="utf-8")
    except OSError:
        # A read-only install directory is not worth interrupting the app for;
        # the choice simply will not survive a restart.
        pass
