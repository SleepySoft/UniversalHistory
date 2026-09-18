# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Agent API + web frontend server (console, onedir).

Build from the UniversalHistory/ directory:

    pyinstaller packaging/service.spec --distpath dist --workpath build -y

The bundle must ship both the translation catalogues and the static web
frontend (service/web/), which __main__ mounts at "/".
"""

from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "universal_history"

datas = [
    (str(PKG / "translations"), "universal_history/translations"),
    (str(PKG / "service" / "web"), "universal_history/service/web"),
]

a = Analysis(
    [str(PKG / "service" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["lunar_python", "uvicorn.lifespan.on", "uvicorn.protocols"],
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
    name="universal-history-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name="universal-history-server",
)
