"""Desktop front-end: `python -m librephonecam.gui`.

A single window that starts the server on open, shows the QR code, and hands
over the two addresses. Built on tkinter so a frozen build needs nothing
beyond the standard library.

tkinter has no cascade, so every widget that follows the palette registers
itself here and gets repainted when the theme changes.
"""

from __future__ import annotations

import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox

from . import __app_name__, __version__, i18n, prefs, theme
from .paths import icon_path
from .qr import matrix as qr_matrix
from .runtime import Config, Endpoints, NoNetwork, PortInUse, ServerThread
from .signaling import Hub

FONT = "Segoe UI" if sys.platform == "win32" else "Helvetica"
MONO = "Consolas" if sys.platform == "win32" else "Menlo"

QR_CANVAS = 250


def enable_dpi_awareness() -> None:
    """Stop Windows from bitmap-scaling the window into a blurry mess."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def claim_taskbar_identity() -> None:
    """Give Windows an application id of our own.

    Without it the taskbar groups the window under whichever interpreter is
    hosting it and shows that program's icon instead of ours. Must run before
    the first window exists.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{__app_name__}.{__app_name__}"
        )
    except Exception:
        pass


class AddressRow(tk.Frame):
    """A read-only address with a Copy button."""

    def __init__(self, parent: tk.Misc, app: App, url: str) -> None:
        super().__init__(parent)
        self.app = app
        self.url = url

        self.entry = tk.Entry(
            self,
            font=(MONO, 10),
            relief="flat",
            highlightthickness=1,
        )
        self.entry.insert(0, url)
        self.entry.configure(state="readonly")
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)

        self.button = tk.Button(
            self,
            font=(FONT, 9, "bold"),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            width=9,
            command=self.copy,
        )
        self.button.pack(side="left", padx=(8, 0), ipady=5)

        self._flashing = False
        app.styled(self, bg="surface")
        app.styled(
            self.entry,
            bg="surface2",
            fg="text",
            readonlybackground="surface2",
            insertbackground="text",
            selectbackground="accent",
            selectforeground="onAccent",
            highlightbackground="line",
            highlightcolor="accent",
        )
        self._style_button()

    def _style_button(self) -> None:
        p = self.app.palette()
        self.button.configure(
            bg=p["surface2"],
            fg=p["text"],
            activebackground=p["accent"],
            activeforeground=p["onAccent"],
        )

    def copy(self) -> None:
        self.app.copy_to_clipboard(self.url)
        p = self.app.palette()
        self._flashing = True
        self.button.configure(
            text=i18n.t(self.app.lang, "copied"), bg=p["good"], fg=p["onGood"]
        )
        self.after(1200, self._restore)

    def _restore(self) -> None:
        self._flashing = False
        self.refresh()

    def refresh(self) -> None:
        """Re-apply label and colours after a theme or language change."""
        if self._flashing:
            p = self.app.palette()
            self.button.configure(
                text=i18n.t(self.app.lang, "copied"), bg=p["good"], fg=p["onGood"]
            )
            return
        self.button.configure(text=i18n.t(self.app.lang, "copy"))
        self._style_button()


class App:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.hub = Hub(ice_servers=config.ice_servers())
        self.server = ServerThread(config, self.hub)
        self.endpoints: Endpoints | None = None
        self._booted = False
        self._closed = False

        stored = prefs.load()
        self.lang: str = stored["lang"]
        self.theme: str = stored["theme"]

        self._styles: list[tuple[tk.Misc, dict[str, str]]] = []
        self._rows: list[AddressRow] = []
        self._dot_key = "muted"
        self._status = ("waitingPhone", {})

        self.root = tk.Tk()
        self.root.title(__app_name__)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.icon_applied = self._apply_icon()

        self._build()
        self.apply_theme()
        self.apply_lang()
        self.root.after(50, self.boot)

    def _apply_icon(self) -> bool:
        """Put the logo on the window, the taskbar and every dialog.

        `default=` makes it apply to message boxes too, which would otherwise
        keep the bare Tk feather.
        """
        ico = icon_path("ico")
        if ico is not None and sys.platform == "win32":
            try:
                # `default=` covers dialogs, which would otherwise keep the
                # bare Tk feather; the plain call sets this window's own icon.
                self.root.iconbitmap(default=str(ico))
                self.root.iconbitmap(str(ico))
                return True
            except tk.TclError:
                pass

        png = icon_path("png")
        if png is not None:
            try:
                # Tk drops the image if nothing holds a reference to it.
                self._icon_image = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, self._icon_image)
                return True
            except tk.TclError:
                pass
        return False

    # -- palette plumbing -------------------------------------------------

    def palette(self) -> dict[str, str]:
        return theme.palette(self.theme)

    def styled(self, widget, **mapping: str):
        """Register `widget` so its options track the palette."""
        self._styles.append((widget, mapping))
        return widget

    def apply_theme(self) -> None:
        p = self.palette()
        self.root.configure(bg=p["bg"])
        for widget, mapping in self._styles:
            widget.configure(**{opt: p[key] for opt, key in mapping.items()})
        self.dot.itemconfigure(self._dot_id, fill=p[self._dot_key])
        self.theme_btn.configure(text=theme.icon(self.theme))
        for row in self._rows:
            row.refresh()

    def apply_lang(self) -> None:
        self.lang_btn.configure(text=i18n.other(self.lang).upper())
        self.phone_title.configure(text=i18n.t(self.lang, "phoneStep"))
        self.stream_title.configure(text=i18n.t(self.lang, "streamStep"))
        self.stream_hint.configure(text=i18n.t(self.lang, "streamHint"))
        self.open_btn.configure(text=i18n.t(self.lang, "openPreview"))
        self.more_btn.configure(text=i18n.t(self.lang, "otherAddresses"))

        regenerated = bool(self.endpoints and self.endpoints.cert_regenerated)
        self.phone_hint.configure(
            text=i18n.t(self.lang, "phoneHintNew" if regenerated else "phoneHint")
        )
        self.phone_hint_key = "phoneHintNew" if regenerated else "phoneHint"
        self._recolour_phone_hint()

        for row in self._rows:
            row.refresh()
        self.render_status()

    def _recolour_phone_hint(self) -> None:
        p = self.palette()
        warn = self.phone_hint_key == "phoneHintNew"
        self.phone_hint.configure(fg=p["warn"] if warn else p["muted"])

    def toggle_theme(self) -> None:
        self.theme = theme.other(self.theme)
        prefs.save(self.lang, self.theme)
        self.apply_theme()
        self._recolour_phone_hint()

    def toggle_lang(self) -> None:
        self.lang = i18n.other(self.lang)
        prefs.save(self.lang, self.theme)
        self.apply_lang()

    # -- construction -----------------------------------------------------

    def _build(self) -> None:
        outer = self.styled(tk.Frame(self.root, padx=22, pady=16), bg="bg")
        outer.pack(fill="both", expand=True)

        header = self.styled(tk.Frame(outer), bg="bg")
        header.pack(fill="x")
        self.styled(
            tk.Label(header, text=__app_name__, font=(FONT, 16, "bold")),
            bg="bg", fg="text",
        ).pack(side="left")
        self.styled(
            tk.Label(header, text=f"v{__version__}", font=(FONT, 9)), bg="bg", fg="muted"
        ).pack(side="left", padx=(8, 0), pady=(6, 0))

        self.lang_btn = self.styled(
            tk.Button(
                header, font=(FONT, 9, "bold"), relief="flat", borderwidth=0,
                cursor="hand2", width=4, command=self.toggle_lang,
            ),
            bg="surface2", fg="muted", activebackground="line", activeforeground="text",
        )
        self.lang_btn.pack(side="right", ipady=3)

        self.theme_btn = self.styled(
            tk.Button(
                header, font=(FONT, 11), relief="flat", borderwidth=0,
                cursor="hand2", width=4, command=self.toggle_theme,
            ),
            bg="surface2", fg="muted", activebackground="line", activeforeground="text",
        )
        self.theme_btn.pack(side="right", padx=(0, 6), ipady=1)

        status = self.styled(tk.Frame(outer), bg="bg")
        status.pack(fill="x", pady=(12, 14))
        self.dot = self.styled(
            tk.Canvas(status, width=10, height=10, highlightthickness=0), bg="bg"
        )
        self.dot.pack(side="left", pady=(3, 0))
        self._dot_id = self.dot.create_oval(1, 1, 9, 9, fill="#8b939f", outline="")
        self.status_label = self.styled(
            tk.Label(status, font=(FONT, 10)), bg="bg", fg="text"
        )
        self.status_label.pack(side="left", padx=(8, 0))

        # The QR plate stays white in both themes: phone cameras expect dark
        # modules on a light background and a dark plate hurts recognition.
        self.qr_canvas = tk.Canvas(
            outer, width=QR_CANVAS, height=QR_CANVAS, bg="#ffffff", highlightthickness=0
        )
        self.qr_canvas.pack()

        body = self.styled(tk.Frame(outer), bg="surface")
        body.pack(fill="x", pady=(16, 0))

        self.phone_title, self.phone_hint, self.phone_holder = self._section(body)
        self.stream_title, self.stream_hint, self.stream_holder = self._section(body)
        self.phone_hint_key = "phoneHint"

        footer = self.styled(tk.Frame(outer), bg="bg")
        footer.pack(fill="x", pady=(14, 0))

        self.more_btn = self.styled(
            tk.Button(
                footer, font=(FONT, 9), relief="flat", borderwidth=0,
                cursor="hand2", command=self.show_other_addresses,
            ),
            bg="bg", fg="muted", activebackground="bg", activeforeground="text",
        )

        self.open_btn = self.styled(
            tk.Button(
                footer, font=(FONT, 9, "bold"), relief="flat", borderwidth=0,
                cursor="hand2", padx=14, command=self.open_preview,
            ),
            bg="accent", fg="onAccent",
            activebackground="accentStrong", activeforeground="onAccent",
        )
        self.open_btn.pack(side="right", ipady=5)

    def _section(self, parent: tk.Misc):
        frame = self.styled(tk.Frame(parent, padx=16, pady=14), bg="surface")
        frame.pack(fill="x")
        title = self.styled(
            tk.Label(frame, font=(FONT, 8, "bold"), anchor="w"), bg="surface", fg="muted"
        )
        title.pack(fill="x", pady=(0, 7))
        holder = self.styled(tk.Frame(frame), bg="surface")
        holder.pack(fill="x")
        hint = self.styled(
            tk.Label(frame, font=(FONT, 8), anchor="w", justify="left"),
            bg="surface", fg="muted",
        )
        hint.pack(fill="x", pady=(7, 0))
        return title, hint, holder

    # -- lifecycle --------------------------------------------------------

    def boot(self) -> None:
        # Guard against a second start: the scheduled callback and an explicit
        # call would otherwise race and fight over the same ports.
        if self._booted:
            return
        self._booted = True

        try:
            self.endpoints = self.server.start()
        except NoNetwork as exc:
            self.fail("errNoNetworkTitle", "errNoNetwork", str(exc))
            return
        except PortInUse as exc:
            self.fail("errPortTitle", "errPort", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - last resort, must reach the user
            self.fail("errStartTitle", None, str(exc))
            return

        self.render_endpoints(self.endpoints)
        self.poll_status()

    def fail(self, title_key: str, body_key: str | None, detail: str) -> None:
        self._dot_key = "danger"
        title = i18n.t(self.lang, title_key)
        body = (
            i18n.t(self.lang, body_key, detail=detail, app=__app_name__)
            if body_key
            else detail
        )
        messagebox.showerror(f"{__app_name__} - {title}", body, parent=self.root)
        self.close()

    def render_endpoints(self, ep: Endpoints) -> None:
        self.draw_qr(ep.phone_url)

        for holder, url in ((self.phone_holder, ep.phone_url),
                            (self.stream_holder, ep.view_url)):
            row = AddressRow(holder, self, url)
            row.pack(fill="x")
            self._rows.append(row)

        if ep.extra_phone_urls:
            self.more_btn.pack(side="left", pady=(4, 0))
        self.apply_lang()

    def draw_qr(self, data: str) -> None:
        grid = qr_matrix(data)
        modules = len(grid)

        # Integer module size keeps every square crisp; a fractional one makes
        # the code blurry and slower for a camera to lock onto.
        scale = max(1, QR_CANVAS // modules)
        offset = (QR_CANVAS - scale * modules) // 2

        self.qr_canvas.delete("all")
        for y, row in enumerate(grid):
            for x, dark in enumerate(row):
                if not dark:
                    continue
                x0 = offset + x * scale
                y0 = offset + y * scale
                self.qr_canvas.create_rectangle(
                    x0, y0, x0 + scale, y0 + scale, fill="#000000", outline=""
                )

    # -- interaction ------------------------------------------------------

    def copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        # Without this the clipboard contents die with the process on Windows.
        self.root.update()

    def open_preview(self) -> None:
        if self.endpoints:
            webbrowser.open(self.endpoints.view_url)

    def show_other_addresses(self) -> None:
        if not self.endpoints:
            return
        messagebox.showinfo(
            f"{__app_name__} - {i18n.t(self.lang, 'otherAddresses')}",
            i18n.t(
                self.lang,
                "otherAddressesBody",
                addresses="\n".join(self.endpoints.extra_phone_urls),
            ),
            parent=self.root,
        )

    # -- status -----------------------------------------------------------

    def set_status(self, dot: str, key: str, **params: object) -> None:
        self._dot_key = dot
        self._status = (key, params)
        self.render_status()

    def render_status(self) -> None:
        key, params = self._status
        self.status_label.configure(text=i18n.t(self.lang, key, **params))
        self.dot.itemconfigure(self._dot_id, fill=self.palette()[self._dot_key])

    def poll_status(self) -> None:
        """Read the hub from the UI thread rather than pushing from the server.

        The hub is only ever two plain attributes, so sampling it here avoids
        marshalling callbacks across the asyncio thread into tkinter.
        """
        if not self.server.is_running():
            self.set_status("danger", "serverStopped")
            return

        s = self.hub.status()
        count = s["viewers"]
        viewers = i18n.t(self.lang, "viewerOne" if count == 1 else "viewerMany")

        if s["sender"] and count:
            self.set_status("good", "streaming",
                            device=s["senderLabel"], count=count, viewers=viewers)
        elif s["sender"]:
            self.set_status("warn", "phoneWaiting", device=s["senderLabel"])
        elif count:
            self.set_status("warn", "viewersWaiting", count=count, viewers=viewers)
        else:
            self.set_status("muted", "waitingPhone")

        self.root.after(500, self.poll_status)

    def close(self) -> None:
        # Reachable twice: once from the error path, once from the window
        # manager or a caller's cleanup.
        if self._closed:
            return
        self._closed = True
        self.server.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    enable_dpi_awareness()
    claim_taskbar_identity()
    App(Config()).run()


if __name__ == "__main__":
    main()
