"""Generate the application icon: LibrePhoneCam.ico and LibrePhoneCam.png.

Pure standard library on purpose: the icon is a build input, and pulling
Pillow in just to draw a few shapes would put a compiled dependency in the
release pipeline for no reason.

The .ico is what Windows uses for the executable, the window and the taskbar.
The .png is what Tk uses for the window icon everywhere else.

Run with: python build-tools/make_icon.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICO_OUT = HERE / "LibrePhoneCam.ico"
PNG_OUT = HERE / "LibrePhoneCam.png"

SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZE = 256
SUPERSAMPLE = 4  # rendered at 4x then averaged down, for clean edges

ACCENT = (59, 130, 246)  # #3b82f6, the accent colour of the app and web pages
DARK = (11, 13, 16)  # #0b0d10
WHITE = (255, 255, 255)


def _rounded_rect(x: float, y: float, cx: float, cy: float,
                  w: float, h: float, r: float) -> bool:
    """Signed-distance test for a rounded rectangle centred on (cx, cy).

    Only the corner quadrant is a circle test; along the straight edges one of
    the two offsets clamps to zero, which is what keeps the sides flat.
    """
    qx = max(abs(x - cx) - (w / 2 - r), 0.0)
    qy = max(abs(y - cy) - (h / 2 - r), 0.0)
    return math.hypot(qx, qy) <= r


def _render(size: int) -> list[bytes]:
    """One RGBA row per line, drawn at `size` pixels.

    A phone body with a lens in it. The lens alone reads as any camera; the
    body is what makes it a *phone* camera at a glance.
    """
    big = size * SUPERSAMPLE
    cx = cy = big / 2

    plate_r = big * 0.22

    phone_w, phone_h = big * 0.46, big * 0.70
    phone_r = big * 0.10
    # Slightly above centre so the body does not look bottom-heavy inside the
    # rounded plate.
    phone_cy = cy - big * 0.005

    lens_outer = big * 0.150
    lens_inner = big * 0.104
    glint_r = big * 0.030
    glint_x, glint_y = cx + big * 0.048, phone_cy - big * 0.052

    hi: list[list[tuple[int, int, int, int]]] = []
    for py in range(big):
        row: list[tuple[int, int, int, int]] = []
        for px in range(big):
            x, y = px + 0.5, py + 0.5

            if not _rounded_rect(x, y, cx, cy, big, big, plate_r):
                row.append((0, 0, 0, 0))
                continue

            if not _rounded_rect(x, y, cx, phone_cy, phone_w, phone_h, phone_r):
                row.append((*ACCENT, 255))
                continue

            d = math.hypot(x - cx, y - phone_cy)
            if math.hypot(x - glint_x, y - glint_y) <= glint_r:
                row.append((*WHITE, 255))
            elif d <= lens_inner:
                row.append((*DARK, 255))
            elif d <= lens_outer:
                row.append((*ACCENT, 255))
            else:
                row.append((*WHITE, 255))
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


def _png(size: int, rows: list[bytes]) -> bytes:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)  # filter type 0 per scanline
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    rendered = {size: _render(size) for size in sorted({*SIZES, PNG_SIZE})}

    images = [(size, _dib(size, rendered[size])) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)

    entries = bytearray()
    for size, data in images:
        # 256 is stored as 0; the field is a single byte.
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    ICO_OUT.write_bytes(header + bytes(entries) + b"".join(d for _, d in images))
    PNG_OUT.write_bytes(_png(PNG_SIZE, rendered[PNG_SIZE]))

    print(f"wrote {ICO_OUT.name} ({ICO_OUT.stat().st_size:,} bytes, "
          f"sizes: {', '.join(map(str, SIZES))})")
    print(f"wrote {PNG_OUT.name} ({PNG_OUT.stat().st_size:,} bytes, {PNG_SIZE}px)")


if __name__ == "__main__":
    main()
