#!/bin/bash

APP_PATH="dist/main.app"

echo "기존 서명 제거 중..."
find "$APP_PATH" -type f -perm +111 -exec codesign --remove-signature {} \; 2>/dev/null || true
codesign --remove-signature "$APP_PATH" 2>/dev/null || true

echo "1. 내부 Mach-O 바이너리 전체 서명 중..."
find "$APP_PATH" -type f -perm +111 -exec file {} \; | grep 'Mach-O' | cut -d: -f1 | while read -r BIN; do
    echo "서명 중: $BIN"
    codesign --force --sign - --timestamp=none "$BIN"
done

echo "1.5. 내부 Frameworks, 라이브러리 서명 중..."
find "$APP_PATH/Contents/Frameworks" -type f -perm +111 -exec file {} \; 2>/dev/null | grep 'Mach-O' | cut -d: -f1 | while read -r FRAME_BIN; do
    echo "서명 중: $FRAME_BIN"
    codesign --force --sign - --timestamp=none "$FRAME_BIN"
done

echo "2. .app 전체 서명 중..."
codesign --force --sign - --timestamp=none --generate-entitlement-der "$APP_PATH"

echo "3. 서명 검증..."
codesign --verify --deep --strict --verbose=4 "$APP_PATH"

echo "4. 격리 속성 제거..."
xattr -d com.apple.quarantine "$APP_PATH" 2>/dev/null

echo "완료!"


# 쉘 실행 명령어
# chmod +x sign_app.sh
# ./sign_app.sh

# 서명 상태 OK 확인
# codesign -v dist/main.app
# spctl --assess --verbose dist/main.app
# "accepted" 나와야 정상 실행됨