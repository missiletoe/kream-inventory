# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 프로젝트의 src 디렉토리 내의 모든 모듈 수집
hidden_imports = collect_submodules('src.kream_inventory')

# 어플리케이션 데이터 파일 수집 (이미지, 아이콘 등)
datas = collect_data_files('src.kream_inventory', include_py_files=False)

# 필요한 데이터 파일 직접 추가 (예: config.ini)
if os.path.exists('src/kream_inventory/config.ini'):
    datas.append(('src/kream_inventory/config.ini', 'kream_inventory'))

# 애셋 디렉토리가 있다면 추가
if os.path.isdir('src/kream_inventory/assets'):
    datas.append(('src/kream_inventory/assets', 'kream_inventory/assets'))

a = Analysis(
    ['src/kream_inventory/__init__.py'],  # 메인 스크립트 경로 수정
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,  # 최적화 레벨 증가
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kream_inventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 애플리케이션이므로 콘솔 비활성화
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/kream_inventory/assets/icon.ico' if os.path.exists('src/kream_inventory/assets/icon.ico') else None,
)

# macOS 용 번들 생성
app = BUNDLE(
    exe,
    name='kream_inventory.app',
    icon='src/kream_inventory/assets/icon.icns' if os.path.exists('src/kream_inventory/assets/icon.icns') else None,
    bundle_identifier='com.missiletoe.kream_inventory',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '0.2.0',
    },
)
