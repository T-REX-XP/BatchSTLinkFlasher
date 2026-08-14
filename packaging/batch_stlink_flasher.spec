# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for Batch ST-Link Flasher (Windows).

Prefer:
  powershell -File scripts\\build_app.ps1

Produces:
  dist/BatchSTLinkFlasher/BatchSTLinkFlasher.exe   (+ Qt / Python deps)

OpenOCD is NOT in this step — scripts\\build_installer.ps1 copies it under
tools\\openocd and compiles Setup.exe (single installer file for operators).

Why onedir (not --onefile):
  - Reliable PySide6 / Qt plugins
  - Sibling tools\\openocd tree for the bundled programmer
  - Inno Setup packages the folder into one Setup.exe
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent
SRC = ROOT / "src"
ASSETS = SRC / "batch_stlink_flasher" / "assets"
ICON = ASSETS / "app_icon.ico"
ENTRY = SRC / "batch_stlink_flasher" / "__main__.py"

datas = [(str(ASSETS), "batch_stlink_flasher/assets")]
binaries = []
hiddenimports = []

tmp = collect_all("PySide6")
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

a = Analysis(
    [str(ENTRY)],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BatchSTLinkFlasher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BatchSTLinkFlasher",
)
