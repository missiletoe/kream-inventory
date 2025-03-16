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

# KNOWN ISSUES
# 1. Apple Silicon(M1/M2/M3)에서 실행할 때 서명이 필수인데 빠져서 빌드 app 실행 불가
# Adhoc 서명 수동 처리 명령어:
'''
codesign --force --sign - --timestamp=none dist/main.app/Contents/MacOS/main
codesign --force --sign - --timestamp=none dist/main.app
'''
# 2. --deep은 일부 macOS 버전에서 deprecated
# 
# ADDITIONAL INFO
# Apple Silicon 환경에서는 서명 없이 실행 거의 불가 (macOS 13~15)
# py2app 빌드시 자동 adhoc 서명이 실패하면 무서명 상태로 빌드됨 → 직접 서명 필요
# SIGKILL Code Signature Invalid는 macOS 커널이 직접 앱을 종료시킨 것임