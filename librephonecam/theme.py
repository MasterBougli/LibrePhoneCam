"""Colour palettes for the desktop window.

Deliberately the same values as web/static/style.css, so the app and the page
on the phone look like one product.
"""

from __future__ import annotations

DARK = {
    "bg": "#0b0d10",
    "surface": "#14171c",
    "surface2": "#1c2027",
    "line": "#272c34",
    "text": "#e8ebf0",
    "muted": "#8b939f",
    "accent": "#3b82f6",
    "accentStrong": "#2563eb",
    "good": "#22c55e",
    "warn": "#f59e0b",
    "danger": "#ef4444",
    "onAccent": "#ffffff",
    "onGood": "#0b0d10",
}

LIGHT = {
    "bg": "#f4f6f9",
    "surface": "#ffffff",
    "surface2": "#eef1f6",
    "line": "#d8dee7",
    "text": "#10151c",
    "muted": "#5c6672",
    "accent": "#2563eb",
    "accentStrong": "#1d4ed8",
    "good": "#16a34a",
    "warn": "#b45309",
    "danger": "#dc2626",
    "onAccent": "#ffffff",
    "onGood": "#ffffff",
}

PALETTES = {"dark": DARK, "light": LIGHT}


def palette(name: str) -> dict[str, str]:
    return PALETTES.get(name, DARK)


def other(name: str) -> str:
    return "dark" if name == "light" else "light"


def icon(name: str) -> str:
    """Glyph for the toggle: show where the click will take you."""
    return "☾" if name == "light" else "☀"
