"""Generate assets/LibrePhoneCam.ico.

Pure standard library on purpose: the icon is a build input, and pulling
Pillow in just to draw two circles would put a compiled dependency in the
release pipeline for no reason.

Run with: python build-tools/make_icon.py
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent / "LibrePhoneCam.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)
SUPERSAMPLE = 4  # rendered at 4x then averaged down, for clean edges

ACCENT = (59, 130, 246)  # #3b82f6, the accent colour of the app and web pages
DARK = (11, 13, 16)  # #0b0d10
WHITE = (255, 255, 255)


def _rounded_square(x: float, y: float, size: float) -> bool:
    """Signed-distance test for a rounded square centred in `size`.

    Only the corner quadrant is a circle test; along the straight edges one of
    the two offsets clamps to zero, which is what keeps the sides square.
    """
    r = size * 0.22
    half = size / 2
    qx = max(abs(x - half) - (half - r), 0.0)
    qy = max(abs(y - half) - (half - r), 0.0)
    return math.hypot(qx, qy) <= r


def _render(size: int) -> list[bytes]:
    """One RGBA row per line, drawn at `size` pixels."""
    big = size * SUPERSAMPLE
    cx = cy = big / 2

    lens_outer = big * 0.29
    lens_inner = big * 0.205
    glint_r = big * 0.045
    glint_x, glint_y = cx + big * 0.085, cy - big * 0.095

    # Accumulate at high resolution, then box-filter down to `size`.
    hi: list[list[tuple[int, int, int, int]]] = []
    for py in range(big):
        row: list[tuple[int, int, int, int]] = []
        for px in range(big):
            x, y = px + 0.5, py + 0.5
            if not _rounded_square(x, y, big):
                row.append((0, 0, 0, 0))
                continue

            d = math.hypot(x - cx, y - cy)
            if math.hypot(x - glint_x, y - glint_y) <= glint_r:
                row.append((*WHITE, 255))
            elif d <= lens_inner:
                row.append((*DARK, 255))
            elif d <= lens_outer:
                row.append((*WHITE, 255))
            else:
                row.append((*ACCENT, 255))
        hi.append(row)

    rows: list[bytes] = []
    n = SUPERSAMPLE * SUPERSAMPLE
    for y in range(size):
        out = bytearray()
        for x in range(size):
            r = g = b = a = 0
            for sy in range(SUPERSAMPLE):
                for sx in range(SUPERSAMPLE):
                    pr, pg, pb, pa = hi[y * SUPERSAMPLE + sy][x * SUPERSAMPLE + sx]
                    # Weight colour by coverage so transparent edges do not
                    # darken toward black.
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            if a:
                out += bytes((r // a, g // a, b // a, a // n))
            else:
                out += b"\x00\x00\x00\x00"
        rows.append(bytes(out))
    return rows


def _dib(size: int, rows: list[bytes]) -> bytes:
    """A 32-bit BMP frame, the format every ICO consumer understands.

    PNG-compressed frames are legal since Vista and produce a much smaller
    file, but System.Drawing and several icon parsers still choke on them, so
    the extra bytes buy real compatibility.
    """
    # Height is doubled: the DIB covers the colour bitmap plus the AND mask.
    header = struct.pack(
        "<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0
    )

    pixels = bytearray()
    for row in reversed(rows):  # BMP scanlines run bottom-up
        for i in range(0, len(row), 4):
            r, g, b, a = row[i], row[i + 1], row[i + 2], row[i + 3]
            pixels += bytes((b, g, r, a))  # BGRA on disk

    # The AND mask is ignored for 32-bit icons, but the rows must still be
    # there and padded to a 4-byte boundary.
    stride = ((size + 31) // 32) * 4
    mask = b"\x00" * (stride * size)

    return header + bytes(pixels) + mask


def main() -> None:
    images = [(size, _dib(size, _render(size))) for size in SIZES]

    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)

    entries = bytearray()
    for size, data in images:
        # 256 is stored as 0; the field is a single byte.
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(header + bytes(entries) + b"".join(d for _, d in images))
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, sizes: {', '.join(map(str, SIZES))})")


if __name__ == "__main__":
    main()
