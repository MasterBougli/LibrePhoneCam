"""QR generation, so the phone is never handed a typed-in IP address."""

from __future__ import annotations

import io

import qrcode


def _code(data: str) -> qrcode.QRCode:
    # A 2-module quiet zone is the practical minimum for a camera to lock on.
    # Low error correction keeps the code small, which is plenty for a short
    # URL shown on a clean background.
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(data)
    qr.make(fit=True)
    return qr


def matrix(data: str) -> list[list[bool]]:
    """Row-major grid of modules, for callers that draw it themselves."""
    return _code(data).get_matrix()


def render(data: str) -> str:
    """The same code as text, for the console."""
    buf = io.StringIO()
    # `invert=True` draws dark modules as light half-blocks, which is what a
    # phone camera expects on the light-on-dark terminals most people run.
    _code(data).print_ascii(out=buf, invert=True)
    return buf.getvalue().rstrip("\n")
