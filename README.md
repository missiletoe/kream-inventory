# 📦 크림 보관판매 매크로 by missiletoe 🚀🦶🏻🎄

크림 보관판매 매크로는 Python 기반으로 만들어진 매크로 프로그램입니다.

Windows, macOS 모두 실행 가능하며, **무료**입니다.

Chrome과 Selenium을 이용해 매크로가 가동되며, PyQt를 통해 GUI가 제공됩니다.

<img width="1264" alt="Screenshot 2025-03-10 at 06 16 04" src="https://github.com/user-attachments/assets/71c3f7ef-84b0-4eef-b15d-daf82af090fb" />

## 각 버튼의 주요 기능

- **로그인**: 아이디와 비밀번호를 입력해 크림에 로그인합니다.
   - **이 프로그램은 따로 데이터베이스를 두지 않습니다. 즉, 사용자의 크림 아이디와 비밀번호는 오직 프로그램을 실행하는 PC에서만 입력됩니다.**
- **검색**: 키워드로 크림 제품을 검색합니다. 가격과 거래량을 확인할 수 있습니다.
- **상세정보검색**: 선택한 제품의 상세 정보를 확인합니다. 발매가, 모델번호, 출시일, 대표 색상을 확인할 수 있습니다.
- **매크로 시작**: 8~18초 사이로 매크로가 실행됩니다. 유저가 보관판매를 맡길 제품의 사이즈와 수량, 그리고 보관판매 시도 주기를 선택할 수 있습니다.

## 설치 방법

- 터미널 또는 CMD에 Git을 설치하고, 이 Git을 clone하거나 [GitHub](https://github.com/missiletoe/kream-inventory/)에서 Git 폴더를 다운받습니다:

   ```bash
   git clone https://github.com/missiletoe/kream-inventory.git
   ```

- 또는 [.zip 파일](https://github.com/missiletoe/kream-inventory/archive/refs/heads/main.zip)을 다운받아 압축을 풀어 사용합니다.

## 사용 방법 [macOS]

- [build_and_run.command](https://github.com/missiletoe/kream-inventory/blob/main/build_and_run.command)를 터미널로 실행시키면 필요 패키지 설치 후 창이 나타납니다.

## 사용 방법 [Windows]

- [build_and_run.bat](https://github.com/missiletoe/kream-inventory/blob/main/build_and_run.bat)을 CMD로 실행시키면 필요 패키지 설치 후 창이 나타납니다.
   - Python 및 Qt Designer 설치 시 설치에 동의를 묻는 단계가 나오는데 'y'를 눌러주시면 넘어갑니다.

## (3/18) 기존에 이전 버전을 다운 받아 사용하시는 분들 주목

- 윈도우 환경에서의 배치 파일(.bat), 맥OS 환경에서의 커맨드 파일(.command)가 대거 수정되었습니다.
- 파이썬 가상환경 설정 경로 및 필수 패키지가 바꼈으니 기존 파일은 지워주시고 새로 파일을 다운받아 사용하시기 바랍니다.
