# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# PyQt6 관련 임포트와 플러그인 설정
from PyQt6.QtCore import QLibraryInfo
qt_plugins_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
print(f"QT 플러그인 경로: {qt_plugins_path}")

# 프로젝트의 src 디렉토리 내의 모든 모듈 수집
hidden_imports = collect_submodules('src')
hidden_imports.extend([
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'selenium', 'requests', 'chromedriver_autoinstaller'
])

# 어플리케이션 데이터 파일 수집 (이미지, 아이콘 등)
datas = []

# 폴더 또는 파일 전체를 데이터로 추가
if os.path.exists('src'):
    datas.append(('src', 'src'))

# PyQt6 플러그인 추가
datas.append((qt_plugins_path, "PyQt6/Qt6/plugins"))

# 필요한 데이터 파일 직접 추가 (예: config.ini)
if os.path.exists('src/config.ini'):
    datas.append(('src/config.ini', '.'))
else:
    # config.ini 파일이 없으면 생성
    print("config.ini 파일을 생성합니다...")
    from src.core.config import ConfigManager
    config = ConfigManager('src/config.ini')
    print("config.ini 파일 생성 완료")
    datas.append(('src/config.ini', '.'))

# 애셋 디렉토리가 있다면 추가
if os.path.isdir('src/assets'):
    datas.append(('src/assets', 'src/assets'))

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],  # 이 부분을 비워서 onedir 모드로 설정
    exclude_binaries=True,  # onedir 모드를 위해 True로 설정
    name='kream_inventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS에서 필요한 argv 에뮬레이션 활성화
    target_arch=None,
    entitlements_file=None,
    icon='src/assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kream_inventory',
)

app = BUNDLE(
    coll,  # exe 대신 coll을 사용
    name='kream_inventory.app',
    icon='src/assets/icon.icns',
    bundle_identifier='com.missiletoe.kream_inventory',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '0.2.1',
        'NSPrincipalClass': 'NSApplication',  # 기본 클래스 지정
        'CFBundleDocumentTypes': [],  # 문서 타입 지정
    },
    copyright='Copyright 2025 Missiletoe',
    author='Missiletoe',
    comments='Kream Inventory is a tool for managing your Kream inventory.',
    category='Productivity',
    keywords=['kream', 'inventory', 'management'],
    bundle_version='0.2.1',
    bundle_short_version='0.2.1',
    bundle_version_string='0.2.1',
    bundle_name='Kream Inventory',
    bundle_display_name='Kream Inventory',
)
