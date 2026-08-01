"""Every file the scripts and workflows point at must actually exist.

This exists because a stray wildcard delete once removed requirements.txt from
the working tree, and rebuilding the history from that tree meant no diff ever
showed the loss. Nothing failed until CI ran pip install.

Run with: python tests/test_project.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that drive a build or a run, and therefore must not point at ghosts.
DRIVERS = [
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    "run.bat",
    "run.sh",
    "build.bat",
    "build-tools/LibrePhoneCam.spec",
]

# Anything that looks like a path into this repository.
REFERENCE = re.compile(
    r"(?<![\w.\-/\\])"
    r"((?:tests|build-tools|librephonecam|web)[/\\][\w.\-/\\]*[\w]"
    r"|requirements\.txt)"
)

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok  {label}{(' -> ' + detail) if detail else ''}")
    else:
        failures.append(label)
        print(f"  FAIL {label} {detail}")


def resolve(reference: str, source: Path) -> Path:
    """Where a reference points, given the file that wrote it.

    Workflows and the root scripts run from the repository root; a `-r` inside
    a requirements file resolves relative to that file, which is exactly the
    trap `build-tools/requirements.txt` fell into.
    """
    normalised = reference.replace("\\", "/")
    if source.suffix == ".txt":
        return (source.parent / normalised).resolve()
    return (ROOT / normalised).resolve()


def main() -> int:
    for name in DRIVERS:
        source = ROOT / name
        if not source.is_file():
            check(f"{name} exists", False)
            continue

        text = source.read_text(encoding="utf-8")
        seen = sorted({m.group(1) for m in REFERENCE.finditer(text)})
        missing = [r for r in seen if not resolve(r, source).exists()]
        check(f"{name} references resolve", not missing,
              f"{len(seen)} refs" if not missing else f"missing: {', '.join(missing)}")

    # `-r` includes inside requirements files, which resolve relative to the
    # including file rather than to the working directory.
    for name in ("requirements.txt", "build-tools/requirements.txt"):
        source = ROOT / name
        if not source.is_file():
            check(f"{name} exists", False)
            continue
        includes = re.findall(r"^\s*-r\s+(\S+)", source.read_text(encoding="utf-8"), re.M)
        broken = [i for i in includes if not (source.parent / i).resolve().is_file()]
        self_ref = [i for i in includes if (source.parent / i).resolve() == source.resolve()]
        check(f"{name} includes resolve", not broken, ", ".join(broken))
        check(f"{name} does not include itself", not self_ref, ", ".join(self_ref))

    # The runtime dependencies must be declared, or a fresh clone installs
    # nothing and fails on the first import.
    declared = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for package in ("aiohttp", "cryptography", "qrcode", "colorama"):
        check(f"requirements.txt declares {package}", package in declared)

    # Assets the frozen build and the window both read at runtime.
    for asset in ("build-tools/LibrePhoneCam.ico", "build-tools/LibrePhoneCam.png",
                  "web/index.html", "web/view.html", "build-tools/entry.py"):
        check(f"{asset} present", (ROOT / asset).is_file())

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nproject layout: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
