# -*- mode: python ; coding: utf-8 -*-
# Budowa (z katalogu cursor-api/):
#   pip install pyinstaller
#   python -m PyInstaller giclee_app.spec
#
# Wynik: dist/GicleeApp.exe (one-file, okno bez konsoli)

import os
from pathlib import Path

# Katalog cursor-api/: preferuj cwd (uruchom: cd cursor-api && python -m PyInstaller ...),
# potem folder obok pliku .spec.
ROOT = Path(os.getcwd()).resolve()
if not (ROOT / "giclee_app").is_dir() or not (ROOT / "Komponenty").is_dir():
    try:
        ROOT = Path(SPECPATH).resolve().parent
    except NameError:
        ROOT = Path(os.getcwd()).resolve()

block_cipher = None

a = Analysis(
    [str(ROOT / "giclee_app" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Caly pakiet komponentow (Python uruchamia je osobnym interpreterem)
        (str(ROOT / "Komponenty"), "Komponenty"),
        (str(ROOT / "CHECKLIST_SETUP.md"), "."),
    ],
    hiddenimports=[
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "giclee_app",
        "giclee_app.launcher",
        "giclee_app.component_loader",
        "giclee_app.runtime",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="GicleeApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
