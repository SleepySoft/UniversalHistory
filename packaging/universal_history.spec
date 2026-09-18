# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Universal History desktop app (windowed, onedir).

Build from the UniversalHistory/ directory:

    pyinstaller packaging/universal_history.spec --distpath dist --workpath build -y

The Qt UI loads its translations from universal_history/translations/, so the
JSON catalogues must ship inside the bundle.
"""

from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "universal_history"

datas = [
    (str(PKG / "translations"), "universal_history/translations"),
]

a = Analysis(
    [str(PKG / "main_window.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["lunar_python"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="universal-history",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="universal-history",
)
