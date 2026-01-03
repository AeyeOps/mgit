# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for mgit

import sys
from pathlib import Path

block_cipher = None

# Hidden imports for all providers and dependencies
hiddenimports = [
    # Azure DevOps (v7_1 as used in code)
    'azure',
    'azure.devops',
    'azure.devops.connection',
    'azure.devops.exceptions',
    'azure.devops.v7_1',
    'azure.devops.v7_1.core',
    'azure.devops.v7_1.core.models',
    'azure.devops.v7_1.git',
    'azure.devops.v7_1.git.models',
    # Also include v7_0 for compatibility
    'azure.devops.v7_0',
    'azure.devops.v7_0.core',
    'azure.devops.v7_0.core.models',
    'azure.devops.v7_0.git',
    'azure.devops.v7_0.git.models',
    # MS REST dependencies
    'msrest',
    'msrest.authentication',
    'msrest.exceptions',
    'msrest.serialization',
    # Async libraries
    'aiohttp',
    'yarl',
    'multidict',
    'async_timeout',
    'charset_normalizer',
    'aiosignal',
    'frozenlist',
    # Rich console dependencies
    'rich',
    'rich.console',
    'rich.progress',
    'rich.table',
    'rich.panel',
    'rich.live',
    # YAML support
    'yaml',
    'ruamel.yaml',
    'ruamel.yaml.main',
    'ruamel.yaml.loader',
    'ruamel.yaml.dumper',
    # Typer and dependencies
    'typer',
    'click',
    # Dotenv support
    'dotenv',
    # Python standard library modules that might be missed
    'typing_extensions',
    'importlib_metadata',
    'pkg_resources',
    'email',
    'email.mime',
    'email.mime.multipart',
    'email.mime.text',
]

# Analysis
a = Analysis(
    ['mgit/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include pyproject.toml for version reading
        ('pyproject.toml', '.')
    ],
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

# Remove unnecessary files
a.binaries = [x for x in a.binaries if not x[0].startswith('_ssl')]
a.binaries = [x for x in a.binaries if not x[0].startswith('_hashlib')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Determine output name based on platform
if sys.platform == 'win32':
    exe_name = 'mgit.exe'
else:
    exe_name = 'mgit'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
