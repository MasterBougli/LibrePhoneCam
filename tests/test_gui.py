"""Smoke test for the desktop window.

Builds the real window and boots the real server, but never enters the event
loop, so it runs unattended. Needs a display; skips itself where there is none.

Run with: python tests/test_gui.py
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def free_port() -> int:
    """Ask the OS for a port nothing else holds.

    Hard-coding one is a trap: a background updater or a colleague's dev server
    will eventually own it and the failure looks like a bug in this project.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


HTTPS_PORT = free_port()
HTTP_PORT = free_port()

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok  {label}{(' -> ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  FAIL {label} {detail}")


def main() -> int:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("skipped: tkinter is not available")
        return 0

    from librephonecam import i18n, theme
    from librephonecam.gui import App
    from librephonecam.qr import matrix as qr_matrix
    from librephonecam.runtime import Config

    try:
        app = App(Config(https_port=HTTPS_PORT, http_port=HTTP_PORT, auto_port=False))
    except Exception as exc:  # no display, typically
        print(f"skipped: cannot open a window ({exc})")
        return 0

    try:
        app.boot()
        app.root.update()

        ep = app.endpoints
        check("server started", ep is not None)
        if ep is None:
            return 1

        check("phone url is https on the LAN", ep.phone_url.startswith("https://"), ep.phone_url)
        check("phone url is not localhost", "localhost" not in ep.phone_url, ep.phone_url)
        check("view url is loopback http", ep.view_url == f"http://localhost:{HTTP_PORT}/view", ep.view_url)

        check("two address rows", len(app._rows) == 2, str(len(app._rows)))
        check("phone row shows the phone url", app._rows[0].url == ep.phone_url)
        check("streamlabs row shows the view url", app._rows[1].url == ep.view_url)

        # QR must be drawn, and encode the phone URL rather than anything else.
        drawn = len(app.qr_canvas.find_all())
        expected = sum(sum(1 for d in row if d) for row in qr_matrix(ep.phone_url))
        check("qr code is drawn", drawn > 0, f"{drawn} modules")
        check("qr encodes the phone url", drawn == expected, f"{drawn} == {expected}")
        check("qr plate stays white in any theme", app.qr_canvas["bg"] == "#ffffff")

        app._rows[0].copy()
        check("copy puts the url on the clipboard", app.root.clipboard_get() == ep.phone_url)

        # --- language
        for lang in ("en", "fr"):
            app.lang = lang
            app.apply_lang()
            app.root.update()
            check(
                f"[{lang}] step titles translated",
                app.phone_title.cget("text") == i18n.t(lang, "phoneStep")
                and app.stream_title.cget("text") == i18n.t(lang, "streamStep"),
                app.phone_title.cget("text"),
            )
            check(
                f"[{lang}] status translated",
                app.status_label.cget("text") == i18n.t(lang, "waitingPhone"),
                app.status_label.cget("text"),
            )
            check(
                f"[{lang}] toggle offers the other language",
                app.lang_btn.cget("text") == i18n.other(lang).upper(),
                app.lang_btn.cget("text"),
            )

        check("languages actually differ",
              i18n.t("en", "phoneStep") != i18n.t("fr", "phoneStep"))

        # Every key must exist in both languages, or a switch shows raw keys.
        missing = set(i18n.STRINGS["en"]) ^ set(i18n.STRINGS["fr"])
        check("translation keys match across languages", not missing, str(sorted(missing)))

        # --- theme
        for name in ("dark", "light"):
            app.theme = name
            app.apply_theme()
            app.root.update()
            p = theme.palette(name)
            check(
                f"[{name}] window background follows the palette",
                app.root.cget("bg") == p["bg"], app.root.cget("bg"),
            )
            check(
                f"[{name}] nested widgets repainted",
                app.status_label.cget("bg") == p["bg"]
                and app._rows[0].entry.cget("readonlybackground") == p["surface2"],
                app._rows[0].entry.cget("readonlybackground"),
            )
            check(
                f"[{name}] toggle offers the other theme",
                app.theme_btn.cget("text") == theme.icon(name),
            )

        check("themes actually differ", theme.palette("dark")["bg"] != theme.palette("light")["bg"])
        check("palettes define the same keys",
              set(theme.DARK) == set(theme.LIGHT),
              str(sorted(set(theme.DARK) ^ set(theme.LIGHT))))

        # --- server really serving
        with urllib.request.urlopen(f"http://localhost:{HTTP_PORT}/health", timeout=5) as r:
            health = json.load(r)
        check("health endpoint answers",
              health == {"sender": False, "senderLabel": None, "viewers": 0}, str(health))

        with urllib.request.urlopen(f"http://localhost:{HTTP_PORT}/view", timeout=5) as r:
            check("view page is served", r.status == 200 and b"stage" in r.read())

        before = app.server
        app.boot()
        check("boot is not re-entrant", app.server is before)

    finally:
        app.close()

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\ndesktop window: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
