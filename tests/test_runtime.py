"""Port selection: the app must survive a busy 8080 rather than give up.

Run with: python tests/test_runtime.py
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from librephonecam.runtime import Config, PortInUse, pick_port  # noqa: E402

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok  {label}{(' -> ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  FAIL {label} {detail}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    # A free port is returned unchanged.
    port = free_port()
    check("free port is used as-is", pick_port("127.0.0.1", port, True) == port, str(port))

    # An occupied port slides to the next one.
    busy = free_port()
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", busy))
    holder.listen(1)
    try:
        got = pick_port("127.0.0.1", busy, True)
        check("occupied port falls through", got == busy + 1, f"{busy} busy -> {got}")

        # Without fallback the caller is told, instead of being moved silently.
        try:
            pick_port("127.0.0.1", busy, False)
            check("explicit port raises when busy", False, "no exception")
        except PortInUse as exc:
            check("explicit port raises when busy", exc.port == busy, f"port={exc.port}")

        # A whole occupied range still ends in a clear error.
        blockers = []
        try:
            base = free_port()
            for offset in range(3):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.bind(("127.0.0.1", base + offset))
                    s.listen(1)
                    blockers.append(s)
                except OSError:
                    s.close()
            if len(blockers) == 3:
                try:
                    pick_port("127.0.0.1", base, True, span=3)
                    check("exhausted range raises", False, "no exception")
                except PortInUse:
                    check("exhausted range raises", True)
            else:
                print("  --  exhausted range: could not reserve a contiguous block, skipped")
        finally:
            for s in blockers:
                s.close()
    finally:
        holder.close()

    # Defaults are the documented ones, and fallback is on by default.
    cfg = Config()
    check("default ports", (cfg.https_port, cfg.http_port) == (8443, 8080), f"{cfg.https_port}/{cfg.http_port}")
    check("fallback on by default", cfg.auto_port is True)
    check("stun configured by default", cfg.ice_servers() != [])
    check("no-stun yields no ice servers", Config(stun=None).ice_servers() == [])

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nport selection: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
