# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ------------------------------------------------------------
# hidden imports
# ------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("tkinterdnd2")

# ------------------------------------------------------------
# data files
# ------------------------------------------------------------
datas = [
    ("utils", "utils"),   # 你的 BBDown / ffmpeg / aria2 都在这里
]

# ------------------------------------------------------------
# Analysis
# ------------------------------------------------------------
a = Analysis(
    ["main-gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ------------------------------------------------------------
# PYZ
# ------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ------------------------------------------------------------
# EXE
# ------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BBDownGUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # ★ 无控制台
    disable_windowed_traceback=False,
)

# ------------------------------------------------------------
# COLLECT (onedir 核心)
# ------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BBDownGUI",
)