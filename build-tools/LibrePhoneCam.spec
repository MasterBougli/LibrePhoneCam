# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build: one self-contained LibrePhoneCam executable.

Build with:  pyinstaller build-tools/LibrePhoneCam.spec --noconfirm
"""

from pathlib import Path

HERE = Path(SPECPATH)  # noqa: F821 - SPECPATH is injected by PyInstaller
ROOT = HERE.parent

a = Analysis(  # noqa: F821
    [str(HERE / "entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # The web pages are read at runtime, so they must travel with the
        # binary.
        (str(ROOT / "web"), "web"),
        # The icon is needed twice: once below as the executable's own icon,
        # and again at runtime for the window and the taskbar.
        (str(HERE / "LibrePhoneCam.ico"), "."),
        (str(HERE / "LibrePhoneCam.png"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # Trimming what a GUI app never touches; PyInstaller pulls these in through
    # the standard library's optional imports otherwise.
    excludes=["pytest", "setuptools", "pydoc_data", "unittest", "test"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LibrePhoneCam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # No console window: this is a desktop app, and a stray black window reads
    # as "something went wrong" to the people this build is for.
    console=False,
    disable_windowed_traceback=False,
    icon=str(HERE / "LibrePhoneCam.ico"),
)
