# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main-gui.py'],
    pathex=[os.path.abspath('.')],
    datas=[('utils', 'utils')],
    hiddenimports=collect_submodules('tkinterdnd2'),
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='BBDown-GUI',
    console=False,
    upx=False,
)