# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # Add src directory to Python path
    binaries=[],
    datas=[
        ('src/resources', 'resources'),
        ('binaries', 'binaries'),
    ],
    hiddenimports=[
        # Qt imports
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # Async imports
        'qasync',
        'asyncio',
        'aiofiles',
        # Utilities
        'cryptography',
        'psutil',
        'watchdog',
        'numpy',
        'cv2',
        'av',
        # Local modules - explicitly include all packages
        'utils',
        'utils.adb_wrapper',
        'utils.logger',
        'utils.crypto',
        'utils.async_helper',
        'core',
        'core.device_manager',
        'core.file_manager',
        'core.app_manager',
        'core.logcat_streamer',
        'core.shell_manager',
        'core.mirror_engine',
        'gui',
        'gui.main_window',
        'gui.themes',
        'gui.widgets',
        'gui.widgets.file_explorer',
        'gui.widgets.app_list',
        'gui.widgets.logcat_viewer',
        'gui.widgets.device_info',
        'gui.widgets.mirror_viewer',
        'gui.widgets.terminal_widget',
        'gui.dialogs',
        'gui.dialogs.connection_dialog',
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
    [],
    exclude_binaries=True,
    name='ADB-Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/resources/icons/icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADB-Manager',
)
