# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect Flask template and static files
template_files = [
    ('templates', 'templates'),
    ('static', 'static')
]

# Add folder service files
folder_service_files = [
    ('folder_service/server.js', 'folder_service'),
    ('folder_service/package.json', 'folder_service'),
    ('folder_service/node_modules/cors', 'folder_service/node_modules/cors'),
    ('folder_service/node_modules/express', 'folder_service/node_modules/express')
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        *template_files,
        *folder_service_files,
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'xlrd',
        'requests',
        'concurrent.futures',
        'threading',
        'signal',
        'platform',
        'hashlib',
        'pickle',
        'datetime',
        'socket',
        'webbrowser',
        'jinja2.ext',  # Add Jinja2 extensions
        'engineio.async_drivers.threading',  # Add async drivers
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

if sys.platform == 'darwin':
    # On macOS, create a windowed application without console
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ExcelSeeker',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,  # Set to True for debugging
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    # Create .app bundle
    app = BUNDLE(
        exe,
        name='ExcelSeeker.app',
        icon=None,
        bundle_identifier='com.excelseeker.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'CFBundleShortVersionString': '1.0.0',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
else:
    # For Windows and Linux, create console application
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ExcelSeeker',
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