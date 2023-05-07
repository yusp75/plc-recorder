# -*- mode: python ; coding: utf-8 -*-
import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

block_cipher = None


a = Analysis(
    ['main.py','vc.py','db.py','myaml.py','ymenu.py','yio.py','curve.py','util.py'],
    pathex=[],
    binaries=[('yio.py','.'),('db.py','.'),('mtypes.py','.'),('myaml.py','.'),('vc.py','.'),('ymenu.py','.'),('util.py','.'),('curve.py','.'),('resource_rc.py','.')],
    #binaries=[('*.py','.')],
    datas=[('*.ui','.'),('var/*.yaml','var'),('conf/*.yaml','conf'),('icon/*.png','icon'),('resource.qrc','.')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='main',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
