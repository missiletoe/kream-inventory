# setup_mac.py = 맥 app 빌드 스크립트

# py2app 사전 설치 필수. 터미널 명령어:
# pip install py2app

# 스크립트 실행 명령어:
# python setup_mac.py py2app

# KNOWN ISSUES
# Apple Silicon(M1/M2/M3)에서 실행할 때 서명이 필수인데 빠져서 빌드 app 실행 불가

# SOLUTION
# Adhoc 서명 수동 처리 명령어:
'''
xattr -cr dist/main.app

find dist/main.app -type d -name "*.framework" | while read framework; do
    binary_name=$(basename "$framework" .framework)
    binary_path="$framework/Versions/Current/$binary_name"
    if [ -f "$binary_path" ]; then
        codesign --force --sign - "$binary_path"
    fi
done

find dist/main.app -type f -name "*.dylib" | while read lib; do
    codesign --force --sign - "$lib"
done

find dist/main.app/Contents/MacOS -type f | while read exec; do
    codesign --force --sign - "$exec"
done

codesign --force --sign - dist/main.app/Contents/MacOS/main
codesign --force --sign - dist/main.app/Contents/MacOS/python
codesign --force --sign - dist/main.app
'''
# --deep은 일부 macOS 버전에서 deprecated

# ADDITIONAL INFO
# Apple Silicon 환경에서는 서명 없이 실행 거의 불가 (macOS 13~15)
# py2app 빌드시 자동 adhoc 서명이 실패하면 무서명 상태로 빌드됨 → 직접 서명 필요
# SIGKILL Code Signature Invalid는 macOS 커널이 직접 앱을 종료시킨 것임

from setuptools import setup
import py2app.util
py2app.util.codesign_adhoc = lambda *args, **kwargs: None

setup(
    app=['main.py'],
    setup_requires=['py2app'],
    options={
        'py2app': {
            'strip': False
        }
    }
)
