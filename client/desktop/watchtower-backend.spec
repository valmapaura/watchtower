# PyInstaller spec for the Watchtower backend.
#
# Bundles the FastAPI web app (which also runs the motion recorder) into a
# single Windows .exe so the Electron desktop app can launch it without a
# Python install.
#
# Build:  pyinstaller watchtower-backend.spec
import os
from pathlib import Path

# SPECPATH is provided by PyInstaller; repo root is two levels up from client/desktop.
ROOT = Path(SPECPATH).resolve().parent.parent
SRC = ROOT / "src"

block_cipher = None

a = Analysis(
    [str(Path(SPECPATH) / "backend_launcher.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "winotify",
        "watchtower.config",
        "watchtower.detector",
        "watchtower.detector_objects",
        "watchtower.live",
        "watchtower.main",
        "watchtower.notifications",
        "watchtower.recorder",
        "watchtower.source",
        "watchtower.storage",
        "watchtower.writer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude the heavy AI packages — they're installed on-demand by the user
    # (see the "Smart detection" setup in Settings), not bundled.
    excludes=[
        "torch",
        "torchvision",
        "ultralytics",
        "matplotlib",
        "pandas",
        "PIL",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="watchtower-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
