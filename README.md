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

터미널 또는 CMD에 Git을 설치하고, 이 Git을 clone하거나 [GitHub](https://github.com/missiletoe/kream-inventory/)에서 Git 폴더를 다운받습니다:

   ```bash
   git clone https://github.com/missiletoe/kream-inventory.git
   ```

## 사용 방법 [macOS]

- [build_and_run.command](https://github.com/missiletoe/kream-inventory/blob/main/build_and_run.command)를 터미널로 실행시키면 필요 패키지 설치 후 창이 나타납니다.

## 사용 방법 [Windows]

### 방법 1. exe 파일 구동

- [build/exe.win-amd64-3.11](https://github.com/missiletoe/kream-inventory/tree/main/build/exe.win-amd64-3.11) 폴더 내 kream_inventory.exe 를 실행합니다.

### 방법 2. 명령어 파일 구동
- [Python 3.11.9](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)을 설치합니다.
- [build_and_run.bat](https://github.com/missiletoe/kream-inventory/blob/main/build_and_run.bat)을 CMD로 실행시키면 필요 패키지 설치 후 창이 나타납니다.
