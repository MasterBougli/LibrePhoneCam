"""Command line front-end: `python -m librephonecam`.

The desktop app (`librephonecam.gui`) is what most people should use; this
exists for headless setups and for debugging.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from . import __version__, qr
from .runtime import (
    DEFAULT_STUN,
    ROOT,
    Config,
    Endpoints,
    NoNetwork,
    PortInUse,
    serve,
)
from .signaling import Hub

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="librephonecam",
        description="Stream a phone camera into Streamlabs over your local network.",
    )
    p.add_argument("--https-port", type=int, default=8443,
                   help="TLS port the phone connects to (default: 8443)")
    p.add_argument("--http-port", type=int, default=8080,
                   help="plain-HTTP port bound to localhost for Streamlabs (default: 8080)")
    p.add_argument("--host", default="0.0.0.0",
                   help="interface for the TLS listener (default: all)")
    p.add_argument("--ip", default=None,
                   help="override the LAN IP shown in the QR code")
    p.add_argument("--stun", nargs="?", const=DEFAULT_STUN, default=None,
                   metavar="URL",
                   help="contact a STUN server for ICE, off by default; bare "
                        f"--stun uses {DEFAULT_STUN}")
    p.add_argument("--cert-dir", type=Path, default=ROOT / "certs",
                   help="where the self-signed certificate lives")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def config_from(args: argparse.Namespace) -> Config:
    # Someone who names a port on the command line means that port; only the
    # defaults are allowed to slide to the next free one.
    chose_ports = args.https_port != 8443 or args.http_port != 8080
    return Config(
        https_port=args.https_port,
        http_port=args.http_port,
        host=args.host,
        ip=args.ip,
        stun=args.stun,
        cert_dir=args.cert_dir,
        auto_port=not chose_ports,
    )


def print_banner(endpoints: Endpoints) -> None:
    rule = f"{DIM}  {'-' * 58}{RESET}"

    print(f"\n{BOLD}{CYAN}  LibrePhoneCam{RESET} {DIM}v{__version__}{RESET}")
    print(rule)

    print(f"\n{BOLD}  PHONE{RESET} {DIM}- scan this, or type the address below{RESET}\n")
    print(qr.render(endpoints.phone_url))
    print(f"\n     {BOLD}{GREEN}{endpoints.phone_url}{RESET}\n")
    print(f"{DIM}     Safari will warn about the certificate: Show Details >")
    print(f"     visit this website. Once is enough.{RESET}")
    if endpoints.cert_regenerated:
        print(f"{YELLOW}     The certificate was just regenerated - accept it again.{RESET}")
    if endpoints.extra_phone_urls:
        # One per line: a joined list overflows a narrow console and wraps at
        # arbitrary points, which makes the addresses hard to read.
        print(f"{DIM}     If that address does not load, try:")
        for url in endpoints.extra_phone_urls:
            print(f"       {url}")
        print(RESET, end="")

    print(f"\n{BOLD}  RETURN FEED{RESET} {DIM}- Streamlabs, or any browser on this PC{RESET}\n")
    print(f"     {BOLD}{GREEN}{endpoints.view_url}{RESET}\n")
    print(f"{DIM}     Streamlabs: + > Browser, size 1920 x 1080, and tick")
    print(f"     'Refresh browser when scene becomes active'.{RESET}")

    print(f"\n{rule}")
    print(f"{DIM}  Ctrl+C to stop.{RESET}\n")


def status_printer(hub: Hub):
    def render() -> None:
        s = hub.status()
        cam = (
            f"{GREEN}{s['senderLabel']} streaming{RESET}"
            if s["sender"]
            else f"{YELLOW}waiting for phone{RESET}"
        )
        viewers = s["viewers"]
        noun = "viewer" if viewers == 1 else "viewers"
        print(f"  [status] {cam}  {DIM}|{RESET}  {viewers} {noun} connected")

    return render


async def run(config: Config) -> None:
    hub = Hub(ice_servers=config.ice_servers())
    hub.on_change = status_printer(hub)
    # The stop event is never set: the CLI runs until Ctrl+C.
    await serve(config, hub, print_banner, asyncio.Event())


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="  %(levelname)s %(name)s: %(message)s",
    )

    for stream in (sys.stdout, sys.stderr):
        # The QR code and box characters are non-ASCII; the legacy Windows
        # console encoding would raise UnicodeEncodeError on them.
        # line_buffering keeps the banner readable when output is piped to a
        # file, which Python would otherwise hold in a block buffer.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

    # cmd.exe does not enable VT sequence processing on its own, so without
    # this the banner prints raw escape codes instead of colour.
    try:
        import colorama

        colorama.just_fix_windows_console()
    except Exception:  # pragma: no cover - cosmetic only
        pass

    try:
        asyncio.run(run(config_from(args)))
    except KeyboardInterrupt:
        print(f"\n{DIM}  Stopped.{RESET}\n")
    except NoNetwork as exc:
        print(f"\n{YELLOW}  {exc}{RESET}")
        print(f"{YELLOW}  Pass --ip <address> to override.{RESET}\n")
        raise SystemExit(1) from exc
    except PortInUse as exc:
        print(f"\n{YELLOW}  {exc}{RESET}")
        print(f"{YELLOW}  Try --https-port / --http-port.{RESET}\n")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
