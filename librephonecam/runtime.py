"""Server bootstrap shared by the desktop app and the command line.

Keeping this separate from both front-ends means the GUI and the CLI cannot
drift apart: they configure the same `serve()` and read the same `Endpoints`.
"""

from __future__ import annotations

import asyncio
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from aiohttp import web

from . import certs, netinfo
from .app import create_app
from .paths import data_dir
from .signaling import Hub

DEFAULT_STUN = "stun:stun.l.google.com:19302"
ROOT = data_dir()


class NoNetwork(RuntimeError):
    """No routable LAN address, so the phone could never reach us."""


class PortInUse(RuntimeError):
    def __init__(self, port: int, detail: str) -> None:
        super().__init__(f"port {port} is already in use ({detail})")
        self.port = port


@dataclass(frozen=True)
class Config:
    https_port: int = 8443
    http_port: int = 8080
    host: str = "0.0.0.0"
    ip: str | None = None
    stun: str | None = DEFAULT_STUN
    cert_dir: Path = field(default_factory=lambda: ROOT / "certs")
    # Ports like 8080 are popular; refusing to start because some updater got
    # there first is a dead end for anyone who cannot edit a command line.
    auto_port: bool = True

    def ice_servers(self) -> list[dict[str, Any]]:
        return [{"urls": [self.stun]}] if self.stun else []


@dataclass(frozen=True)
class Endpoints:
    phone_url: str
    view_url: str
    extra_phone_urls: list[str]
    cert_regenerated: bool


def pick_port(host: str, preferred: int, allow_fallback: bool, span: int = 20) -> int:
    """Return `preferred`, or the next free port after it.

    Probing with a real bind is the only honest test; SO_REUSEADDR is
    deliberately left off so an occupied Windows port reports as occupied
    instead of being silently shared.
    """
    last: OSError | None = None
    for port in range(preferred, preferred + (span if allow_fallback else 1)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
                return port
            except OSError as exc:
                last = exc
    raise PortInUse(preferred, str(last))


def resolve_ips(config: Config) -> list[str]:
    ips = [config.ip] if config.ip else netinfo.all_lan_ips()
    if not ips:
        raise NoNetwork(
            "No local network address found. Connect to wifi, or pass an "
            "address explicitly."
        )
    return ips


async def serve(
    config: Config,
    hub: Hub,
    on_ready: Callable[[Endpoints], None],
    stop: asyncio.Event,
) -> None:
    """Run until `stop` is set. Calls `on_ready` once both sockets are live."""
    ips = resolve_ips(config)
    ssl_ctx, regenerated = certs.ssl_context(
        config.cert_dir, ips + ["localhost", "127.0.0.1"]
    )

    https_port = pick_port(config.host, config.https_port, config.auto_port)
    http_port = pick_port("127.0.0.1", config.http_port, config.auto_port)

    runner = web.AppRunner(create_app(hub), access_log=None)
    await runner.setup()

    # Two listeners on one app so both peers share the same hub:
    #   - TLS on the LAN, because Safari gates getUserMedia behind a secure
    #     origin and no CA will certify a private address
    #   - plain HTTP on loopback, because Chromium already trusts localhost and
    #     the Streamlabs browser source cannot accept a self-signed certificate
    plan = [
        (web.TCPSite(runner, config.host, https_port, ssl_context=ssl_ctx), https_port),
        (web.TCPSite(runner, "127.0.0.1", http_port), http_port),
    ]

    try:
        for site, port in plan:
            try:
                await site.start()
            except OSError as exc:
                raise PortInUse(port, str(exc)) from exc
    except BaseException:
        await runner.cleanup()
        raise

    on_ready(
        Endpoints(
            phone_url=f"https://{ips[0]}:{https_port}",
            view_url=f"http://localhost:{http_port}/view",
            extra_phone_urls=[f"https://{ip}:{https_port}" for ip in ips[1:]],
            cert_regenerated=regenerated,
        )
    )

    try:
        await stop.wait()
    finally:
        await runner.cleanup()


class ServerThread:
    """Runs `serve()` on its own event loop so a GUI can own the main thread."""

    def __init__(self, config: Config, hub: Hub) -> None:
        self._config = config
        self._hub = hub
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._ready = threading.Event()
        self._endpoints: Endpoints | None = None
        self._error: BaseException | None = None

    def start(self, timeout: float = 30.0) -> Endpoints:
        """Block until the server is listening, or raise why it is not."""
        self._thread = threading.Thread(
            target=self._run, name="librephonecam-server", daemon=True
        )
        self._thread.start()

        if not self._ready.wait(timeout):
            raise TimeoutError("the server did not start in time")
        if self._error is not None:
            raise self._error
        assert self._endpoints is not None
        return self._endpoints

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except BaseException as exc:  # re-raised by start()
            self._error = exc
        finally:
            # Unblocks start() whether we became ready or died trying.
            self._ready.set()

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()

        def ready(endpoints: Endpoints) -> None:
            self._endpoints = endpoints
            self._ready.set()

        await serve(self._config, self._hub, ready, self._stop)

    def stop(self, timeout: float = 5.0) -> None:
        if self._loop and self._stop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread:
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
