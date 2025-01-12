### 크림 보관판매 매크로 ###
### 2024.12.15      ###
### by. missiletoe  ###

from PyQt5.QtCore import QThread, Qt, pyqtSlot, QObject, pyqtSignal  # PyQt5의 코어 모듈에서 필요한 클래스들을 가져옴
from PyQt5.QtWidgets import QApplication, QDialog, QDialogButtonBox, QSpinBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QInputDialog, QMessageBox, QStackedLayout  # PyQt5의 위젯 모듈에서 필요한 클래스들을 가져옴
from PyQt5.QtGui import QPixmap, QIcon, QTextCursor, QFont  # PyQt5의 GUI 모듈에서 필요한 클래스들을 가져옴
from selenium import webdriver  # Selenium 웹드라이버 모듈을 가져옴
from selenium.webdriver.common.by import By  # Selenium의 By 클래스를 가져옴
from selenium.webdriver.support.ui import WebDriverWait  # Selenium의 WebDriverWait 클래스를 가져옴
from selenium.webdriver.support import expected_conditions as EC  # Selenium의 expected_conditions 모듈을 가져옴
from selenium.common.exceptions import NoSuchElementException, TimeoutException  # Selenium의 예외 클래스를 가져옴
import requests  # HTTP 요청을 보내기 위한 requests 모듈을 가져옴
import chromedriver_autoinstaller  # chromedriver-autoinstaller 모듈을 가져옴
from datetime import datetime, timedelta  # 날짜와 시간을 다루기 위한 datetime 모듈을 가져옴
import sys  # 시스템 관련 모듈을 가져옴
import time  # 시간 관련 모듈을 가져옴
import re  # 정규 표현식을 다루기 위한 re 모듈을 가져옴
import pandas as pd  # 데이터프레임을 다루기 위한 pandas 모듈을 가져옴
import os  # 운영체제와 상호작용하기 위한 os 모듈을 가져옴
# import subprocess  # 서브프로세스를 실행하기 위한 subprocess 모듈을 가져옴

# def install(package):  # 패키지를 설치하는 함수 정의
#     try:
#         subprocess.check_call([sys.executable, "-m", "pip", "install", package])  # pip를 사용하여 패키지를 설치
#     except subprocess.CalledProcessError as e:
#         print(f"Failed to install {package}: {e}")  # 설치 실패 시 에러 메시지 출력
#         sys.exit(1)  # 프로그램 종료

# required_packages = {
#     'PyQt5': 'PyQt5',
#     'selenium': 'selenium', 
#     'chromedriver-autoinstaller': 'chromedriver-autoinstaller',
#     'requests': 'requests'
# } # 필요한 패키지들을 딕셔너리로 설정

# def is_package_installed(package_name): # 패키지가 설치되어 있는지 확인하는 함수 정의
#     try:
#         __import__(package_name)
#         return True
#     except ImportError: # 패키지가 설치되어 있지 않을 경우
#         return False

if sys.platform == 'darwin':  # macOS platform
    from AppKit import NSBundle
#     for package_name, pip_name in required_packages.items():
#         if not is_package_installed(package_name):
#             install(pip_name)

# elif sys.platform == 'win32':  # Windows platform
#     for package_name, pip_name in required_packages.items():
#         if not is_package_installed(package_name):
#             install(pip_name)

# if not chromedriver_autoinstaller.get_chrome_version():
#     chromedriver_autoinstaller.install()  # ChromeDriver 설치

options = webdriver.ChromeOptions()  # Chrome 옵션 객체 생성
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'  # 사용자 에이전트 설정
options.add_argument(f'user-agent={user_agent}')  # 사용자 에이전트 옵션 추가
options.add_argument('--headless')  # 헤드리스 모드 옵션 추가
options.add_argument('--disable-gpu')  # GPU 비활성화 옵션 추가
options.add_argument('--no-sandbox')  # 샌드박스 비활성화 옵션 추가
options.add_argument('--disable-dev-shm-usage')  # /dev/shm 사용 비활성화 옵션 추가
options.add_argument('--window-size=768,1024')  # 창 크기 설정 옵션 추가

browser = webdriver.Chrome(options=options)  # Chrome 웹드라이버 객체 생성
product_id = None  # 제품 ID 초기화
inventorypage = f'https://kream.co.kr/inventory/{product_id}'  # 인벤토리 페이지 URL 설정
done = False  # 완료 여부 초기화
is_logged_in = False  # 로그인 여부 초기화
is_brand = False  # 브랜드배송 여부 초기화
left_button_clicked = False # 왼쪽 버튼 클릭 여부 초기화
right_button_clicked = False # 오른쪽 버튼 클릭 여부 초기화
keyword = ''  # 검색어 초기화
sel1 = 1  # 선택된 사이즈 초기화
sel2 = 1  # 선택된 수량 초기화
size_options = []  # 사이즈 옵션 리스트 초기화
repo_path = os.path.dirname(os.path.abspath(sys.argv[0]))  # 저장소 경로 설정
os.environ['QT_PLUGIN_PATH'] = os.path.join(repo_path, '.venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')  # QT 플러그인 경로 설정
print(os.environ['QT_PLUGIN_PATH'])  # QT 플러그인 경로 출력

# 자동화 작업을 처리하는 MacroWorker 클래스 정의
class MacroWorker(QObject):
    log_message = pyqtSignal(str, bool)  # 로그 메시지를 위한 시그널 정의

    def __init__(self, email, password, size, qty, font_size):  # 초기화 함수 정의
        super().__init__()
        self.email = email  # 이메일 초기화
        self.password = password  # 비밀번호 초기화
        self.size = size  # 사이즈 초기화
        self.qty = qty  # 수량 초기화
        self.is_running = True  # 실행 여부 초기화
        self.update_log = lambda msg, html=False: self.log_message.emit(msg, html)  # 로그 업데이트 함수 정의
        self.layout = None  # 레이아웃 초기화

    def setup_layout(self, parent_widget):
        if self.layout is None:
            self.layout = QVBoxLayout()  # 레이아웃 생성
            parent_widget.setLayout(self.layout)  # 부모 위젯에 레이아웃 설정
        else:
            print("Layout already set up")


    def interruptible_sleep(self, total_sleep_time, check_interval=1): # 중단 가능한 sleep 함수 정의
        try:
            for _ in range(int(total_sleep_time / check_interval)): # 주어진 시간동안 반복
                if not self.is_running: # 실행 중이 아닐 경우
                    return False # False 반환
                time.sleep(check_interval) # 주어진 시간만큼 대기
            return True # True 반환

        except KeyboardInterrupt: # 사용자가 Ctrl+C를 눌렀을 경우
            sys.exit(f'[{time.strftime("%H:%M:%S")}] 사용자에 의해 종료되었습니다.') # 종료 메시지 출력


    def run(self):
        self.is_running = True # 실행 여부 설정
        self.macro(self.email, self.password, size=self.size, qty=self.qty) # 매크로 함수 실행


    def macro(self, email, pw, size=sel1, qty=sel2, count=0):
        global done # 완료 여부 전역 변수 설정

        while self.is_running: # 실행 중일 경우

            try:
                if 'https://kream.co.kr/login' in browser.current_url: # 현재 URL이 로그인 페이지일 경우
                    self.relogin(email, pw) # 다시 로그인
            
            except KeyboardInterrupt: # 사용자가 Ctrl+C를 눌렀을 경우
                sys.exit(f'[{time.strftime("%H:%M:%S")}] 사용자에 의해 종료되었습니다.') # 종료 메시지 출력

            if not self.is_running: # 실행 중이 아닐 경우
                return

            if browser.current_url != inventorypage: # 현재 URL이 인벤토리 페이지가 아닐 경우
                browser.get(inventorypage) # 인벤토리 페이지로 이동
                WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로딩 완료 대기

            try:
                box_all = browser.find_elements(By.XPATH, '//div[@class="inventory_size_item"]') # 모든 사이즈 박스 요소 찾기
                count += 1 # 카운트 증가

                if count == 1: # 카운트가 1일 경우
                    for a in range(len(box_all)): # 사이즈 박스 요소의 개수만큼 반복
                        box_all[a].find_element(By.CSS_SELECTOR, 'input').clear() # 사이즈 박스 요소의 입력 요소 초기화
                        box_all[a].find_element(By.CSS_SELECTOR, 'input').send_keys(0) # 사이즈 박스 요소의 입력 요소에 0 입력

                    box = browser.find_element(By.XPATH, f'//div[@class="inventory_size_item"][{size}]') # 선택된 사이즈의 사이즈 박스 요소 찾기
                    box.find_element(By.CSS_SELECTOR, 'input').send_keys(qty) # 사이즈 박스 요소의 입력 요소에 수량 입력

                continue_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[class="complete_btn_box"]'))) # 계속하기 버튼 요소 찾기
                continue_button.click() # 계속하기 버튼 클릭
                self.update_log(f'[{time.strftime("%H:%M:%S")}] {count}회 시도') # 보관판매 시도 메시지 출력
                
                popup = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="toast"]'))) # 팝업 요소 찾기
                time.sleep(1) # 1초 대기

                if 'show' in popup.get_attribute('class'): # 팝업 요소의 클래스에 'show'가 포함되어 있을 경우
                    self.update_log(f'{popup.text}') # 팝업 메시지 출력

                    if popup.text == '인터넷, 와이파이, 모바일 데이터 혹은 비행기모드 설정을 확인해 주시기 바랍니다.': # 팝업 메시지가 '인터넷, 와이파이, 모바일 데이터 혹은 비행기모드 설정을 확인해 주시기 바랍니다.'일 경우
                        block_time = datetime.now() + timedelta(minutes=33, seconds=20) # 차단 시간 설정
                        self.update_log(f'[{time.strftime("%H:%M:%S")}] {block_time.strftime("%H시 %M분 %S초")}에 매크로 재개') # IP 차단 메시지 출력
                        
                        if not self.interruptible_sleep(2000): # 2000초 (33분 20초) 대기
                            return # 반환
                        continue # 다음 반복문으로 이동

                    if not self.interruptible_sleep(7): # 7초 대기
                        return # 반환
                    continue # 다음 반복문으로 이동

                elif box is None: # 사이즈 박스 요소가 없을 경우
                    try: # 예외 처리
                        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로딩 완료 대기

                        if browser.find_element(By.CSS_SELECTOR, 'span[class="title_txt"]').text == '신청내역': # 신청내역 페이지일 경우
                            inventory_opened = True # 인벤토리 페이지 열림 여부 설정

                        self.update_log(f'[{time.strftime("%H:%M:%S")}] 보증금 결제 진행 중...')
                        purchase_button = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//button[@class="display_button large dark_filled active block bold"]')))
                        purchase_button.click() # 보증금 결제하기 버튼 클릭

                        for i in range(1, 4): # 체크박스 요소 클릭을 위한 반복문
                            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, f'//div[@class="title-description-checkbox line"][{i}]'))).click()

                        purchase_button2 = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="layer_container"]//button[@class="display_button large dark_filled active block bold"]')))
                        purchase_button2.click() # 최종 보증금 결제하기 버튼 클릭

                        try:
                            service_error = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="info_txt"]'))).text # 이상한 페이지 요소 찾기
                            if service_error == '일시적인 서비스 장애 입니다.':
                                self.update_log(f'[{time.strftime("%H:%M:%S")}] 일시적인 서비스 장애입니다. 다시 시도합니다.')
                                count = 0
                                browser.refresh()
                                return
                                
                        except:
                            pass

                        try:
                            popup = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="toast sm show"]')))
                            self.update_log(f'{popup.text}') # 팝업 메시지 출력
                            self.update_log(f'[{time.strftime("%H:%M:%S")}] 보증금 결제 실패. 다시 시도합니다.') # 보증금 결제 실패 메시지 출력
                            inventory_opened = False # 인벤토리 페이지 열림 여부 설정
                            browser.refresh() # 브라우저 새로고침
                            count = 0 # 카운트 초기화
                            if not self.interruptible_sleep(click_term - 2): # 클릭 텀 - 2초 대기
                                return # 반환
                            continue # 다음 반복문으로 이동
                                    
                        
                        except TimeoutException:
                            self.update_log(f'[{time.strftime("%H:%M:%S")}] 팝업 요소를 찾을 수 없습니다. 다시 시도합니다.')
                            browser.refresh()
                            return

                        except:
                            self.update_log(f'<br><b>[{time.strftime("%H:%M:%S")}] 보관판매 신청 성공!</b><br>', html=True) # 보관판매 신청 성공 메시지 출력
                            done = True # 완료 여부 설정
                            return # 반환

                    except KeyboardInterrupt: # 사용자가 Ctrl+C를 눌렀을 경우
                        sys.exit(f'[{time.strftime("%H:%M:%S")}] 사용자에 의해 종료되었습니다.') # 종료 메시지 출력

                    except: # 그 외의 예외 발생 시
                        if done == True: # 완료 여부가 True일 경우
                            return # 반환
                        self.update_log(f'[{time.strftime("%H:%M:%S")}] 보증금 결제 중 오류 발생. 다시 시도합니다') # 보증금 결제 오류 메시지 출력
                        browser.refresh() # 브라우저 새로고침
                        if not self.interruptible_sleep(7): # 7초 대기
                            return # 반환
                        continue # 다음 반복문으로 이동
            
            except: # 그 외의 예외 발생 시
                if 'https://kream.co.kr/login' in browser.current_url: # 현재 URL이 로그인 페이지일 경우
                    self.relogin(email, pw) # 다시 로그인
                    count = 0  # Reset count

                if not self.interruptible_sleep(3): # 3초 대기
                    return # 반환
                continue # 다음 반복문으로 이동


    def payment(self):
        global done # 완료 여부 전역 변수 설정

        purchase_button = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//button[@class="display_button large dark_filled active block bold"]'))) # 구매 버튼 요소 찾기
        purchase_button.click() # 구매 버튼 클릭

        for i in range(1, 4):
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, f'//div[@class="title-description-checkbox line"][{i}]'))).click() # 체크박스 요소 클릭

        purchase_button2 = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="layer_container"]//button[@class="display_button large dark_filled active block bold"]'))) # 구매 버튼 요소 찾기
        purchase_button2.click() # 구매 버튼 클릭

        deadline = datetime.now() # 현재 시간 설정
        deadline += timedelta(days=3 if deadline.weekday() in {5, 6} else 2) # 토요일, 일요일일 경우 3일, 그 외의 경우 2일 추가
        self.update_log(f'<br><b>[{time.strftime("%H:%M:%S")}] 보관판매 신청 성공!</b><br>', html=True) # 보관판매 신청 성공 메시지 출력
        self.update_log(f'<b><i>{deadline.strftime("%Y년 %m월 %d일 (%a요일) %H시 %M분").replace("Mon", "월").replace("Tue", "화").replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일")}</i>까지 송장번호를 입력해야 합니다.</b>', html=True) # 송장번호 입력 마감 시간 메시지 출력
        done = True # 완료 여부 설정
        self.interruptible_sleep(3600) # 1시간 대기

        sys.exit(f'[{time.strftime('%H:%M:%S')}] 보관판매 신청 성공! {deadline.strftime("%Y년 %m월 %d일 (%a요일) %H시 %M분").replace("Mon", "월").replace("Tue", "화").replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일")}까지 송장번호를 입력해야 합니다.') # 송장번호 입력 마감 시간 메시지 출력
    

    def relogin(self, email, pw):
        self.update_log(f'<br><b>[{time.strftime("%H:%M:%S")}] 로그인 세션이 만료되었습니다. 다시 로그인합니다.</b><br>', html=True) # 로그인 세션 만료 메시지 출력
        
        browser.get('https://kream.co.kr/login') # 로그인 페이지로 이동
        email_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))) # 이메일 입력 요소 찾기
        password_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))) # 비밀번호 입력 요소 찾기
        email_input.clear() # 이메일 입력 요소 초기화
        email_input.send_keys(email) # 이메일 입력 요소에 이메일 입력
        password_input.clear() # 비밀번호 입력 요소 초기화
        password_input.send_keys(pw) # 비밀번호 입력 요소에 비밀번호 입력
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click() # 로그인 버튼 클릭
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로그인 완료 대기
        self.update_log(f'[{time.strftime("%H:%M:%S")}] 크림에 {email} 계정으로 로그인되었습니다.') # 로그인 완료 메시지 출력


class App(QWidget): # App 클래스 정의
    def __init__(self): # 초기화 함수 정의
        super().__init__() # 부모 클래스 초기화
        self.size_dropdown = QComboBox() # 사이즈 드롭다운 생성
        self.i = 0 # 검색 결과 인덱스 초기화
        self.font_size = 12 # 폰트 크기 초기화
        self.initUI() # UI 초기화 함수 실행


    def initUI(self): # UI 초기화 함수 정의
        global size_options, left_button_clicked, right_button_clicked # 사이즈 옵션 전역 변수 설정

        icon_url = 'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/fd/46/62/fd466276-45df-0152-56e6-8dcd668cb593/AppIcon-0-0-1x_U007epad-0-1-0-85-220.png/1000x0w.png' # 아이콘 URL 설정
        pixmap = QPixmap() # QPixmap 객체 생성
        icon_data = requests.get(icon_url).content # 아이콘 데이터 가져오기
        pixmap.loadFromData(icon_data) # 아이콘 데이터 로드
        self.setWindowIcon(QIcon(pixmap)) # 아이콘 설정
        self.setWindowTitle('크림 보관판매 매크로 by missiletoe') # 제목 설정

        if sys.platform == 'darwin': # macOS 플랫폼일 경우
            app = QApplication.instance() # QApplication 인스턴스 생성
            app.setWindowIcon(QIcon(pixmap)) # 아이콘 설정
            app.setApplicationName('보판뚫자') # 어플리케이션 이름 설정
            bundle = NSBundle.mainBundle() # NSBundle 객체 생성
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary() # 언어별 정보 딕셔너리 생성
            info['CFBundleName'] = '보판뚫자' # 어플리케이션 이름 설정

        if sys.platform == 'darwin': # macOS 플랫폼일 경우
            screen = QApplication.primaryScreen() # 주 화면 객체 생성
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            self.setGeometry(0, 0, int(screen_width // 1.5), int((screen_height // 1.5) - 22)) # 창 크기를 화면의 절반으로 설정
        else: # 그 외의 플랫폼일 경우
            screen = QApplication.primaryScreen() # 주 화면 객체 생성
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            self.setGeometry(0, 0, int(screen_width // 1.5), int(screen_height // 1.5)) # 창 크기를 화면의 절반으로 설정

        # Center the window on the screen
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout() # 수직 레이아웃 객체 생성

        horizontal_layout = QHBoxLayout() # 수평 레이아웃 객체 생성

        self.search_input = QLineEdit(self) # 검색 입력 위젯 생성
        self.search_input.setPlaceholderText('제품명 입력') # 검색 입력 위젯에 플레이스홀더 텍스트 설정
        self.search_input.returnPressed.connect(self.search_product) # 검색 입력 위젯에서 엔터 키를 누르면 제품 검색 함수 실행
        horizontal_layout.addWidget(self.search_input, 3) # 수평 레이아웃에 검색 입력 위젯 추가

        self.search_button = QPushButton('검색', self) # 검색 버튼 생성
        self.search_button.clicked.connect(self.search_product) # 검색 버튼 클릭 시 제품 검색 함수 실행
        horizontal_layout.addWidget(self.search_button, 1) # 수평 레이아웃에 검색 버튼 추가

        self.search_details_button = QPushButton('제품 상세정보', self) # 제품 상세정보 버튼 생성
        self.search_details_button.setEnabled(False) # 제품 상세정보 버튼 비활성화
        self.search_details_button.clicked.connect(self.product_details) # 제품 상세정보 버튼 클릭 시 제품 상세정보 함수 실행
        horizontal_layout.addWidget(self.search_details_button, 1) # 수평 레이아웃에 제품 상세정보 버튼 추가

        horizontal_layout.addSpacing(20)  # Add horizontal gap
        screen = QApplication.primaryScreen() # 주 화면 객체 생성
        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96: # Windows 플랫폼이고 DPI가 96보다 클 경우
            horizontal_layout.addSpacing(20)  # Add horizontal gap

        self.email_input = QLineEdit(self) # 이메일 입력 위젯 생성
        self.email_input.setPlaceholderText('크림 계정 이메일 입력') # 이메일 입력 위젯에 플레이스홀더 텍스트 설정
        self.email_input.setClearButtonEnabled(True) # 이메일 입력 위젯에 지우기 버튼 활성화
        horizontal_layout.addWidget(self.email_input, 3) # 수평 레이아웃에 이메일 입력 위젯 추가

        self.pw_input = QLineEdit(self) # 비밀번호 입력 위젯 생성
        self.pw_input.setEchoMode(QLineEdit.Password) # 비밀번호 입력 위젯의 에코 모드를 비밀번호로 설정
        self.pw_input.setPlaceholderText('비밀번호 입력') # 비밀번호 입력 위젯에 플레이스홀더 텍스트 설정
        self.pw_input.setClearButtonEnabled(True) # 비밀번호 입력 위젯에 지우기 버튼 활성화
        horizontal_layout.addWidget(self.pw_input, 2) # 수평 레이아웃에 비밀번호 입력 위젯 추가

        self.login_button = QPushButton('로그인', self) # 로그인 버튼 생성
        self.pw_input.returnPressed.connect(self.login_button_clicked) # 비밀번호 입력 위젯에서 엔터 키를 누르면 로그인 버튼 클릭
        self.login_button.clicked.connect(self.login_button_clicked) # 로그인 버튼 클릭 시 로그인 함수 실행
        horizontal_layout.addWidget(self.login_button, 1) # 수평 레이아웃에 로그인 버튼 추가

        horizontal_layout.addSpacing(20)  # Add horizontal gap
        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96: # Windows 플랫폼이고 DPI가 96보다 클 경우
            horizontal_layout.addSpacing(20)  # Add horizontal gap

        self.start_button = QPushButton('매크로 시작', self) # 매크로 시작 버튼 생성
        self.start_button.setEnabled(False) # 매크로 시작 버튼 비활성화
        self.start_button.clicked.connect(self.start_macro) # 매크로 시작 버튼 클릭 시 매크로 시작 함수 실행
        horizontal_layout.addWidget(self.start_button, 2) # 수평 레이아웃에 매크로 시작 버튼 추가

        layout.addLayout(horizontal_layout) # 레이아웃에 수평 레이아웃 추가

        log_image_layout = QHBoxLayout() # 로그 이미지 레이아웃 생성

        image_label = QLabel() # 이미지 레이블 생성
        image_label.setObjectName("image_label") # 이미지 레이블에 객체 이름 설정
        image_label.setAlignment(Qt.AlignCenter)  # Center align the image
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        image_label.setFixedWidth(screen_width // 3) # 이미지 너비를 화면의 1/3로 설정
        image_label.setFixedHeight(screen_width // 3) # 이미지 높이를 화면의 1/3로 설정
        image_label.setScaledContents(True)  # 이미지 레이블에 맞게 이미지 크기 조정
        image_label.setPixmap(pixmap)  # 이미지 레이블에 아이콘 설정

        left_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271220.png'
        left_icon = QIcon()
        left_icon_data = requests.get(left_icon_url).content
        left_icon_pixmap = QPixmap()
        left_icon_pixmap.loadFromData(left_icon_data)
        left_icon.addPixmap(left_icon_pixmap) # 왼쪽 아이콘 설정
        self.left_button = QPushButton(left_icon, '', self)  # 왼쪽 버튼 생성
        self.left_button.setFixedSize(50, 50)
        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            self.left_button.setFixedSize(100, 100)
        self.left_button.clicked.connect(self.previous_result)
        self.left_button.setEnabled(False)

        right_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271228.png'
        right_icon = QIcon()
        right_icon_data = requests.get(right_icon_url).content
        right_icon_pixmap = QPixmap()
        right_icon_pixmap.loadFromData(right_icon_data)
        right_icon.addPixmap(right_icon_pixmap) # 오른쪽 아이콘 설정
        self.right_button = QPushButton(right_icon, '', self) # 오른쪽 버튼 생성
        self.right_button.setFixedSize(50, 50)
        if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
            self.right_button.setFixedSize(100, 100)
        self.right_button.clicked.connect(self.next_result)
        self.right_button.setEnabled(False)
        
        # Create a layout to stack the image and buttons
        stacked_layout = QHBoxLayout()
        stacked_layout.addWidget(self.left_button, 0, Qt.AlignLeft | Qt.AlignVCenter)
        stacked_layout.addWidget(image_label)
        stacked_layout.addWidget(self.right_button, 0, Qt.AlignRight | Qt.AlignVCenter)
        
        image_layout = QVBoxLayout()
        image_layout.addLayout(stacked_layout)
        
        log_image_layout.addLayout(image_layout)

        self.log_output = QTextEdit(self) # 로그 출력 위젯 생성 
        self.log_output.setReadOnly(True) # 로그 출력 위젯을 읽기 전용으로 설정
        self.log_output.setPlaceholderText('제품 정보와 매크로 활동 기록이 여기에 표시됩니다.') # 로그 출력 위젯에 플레이스홀더 텍스트 설정
        log_image_layout.addWidget(self.log_output) # 로그 출력 위젯 추가

        layout.addLayout(log_image_layout) # 메인 레이아웃에 수평 레이아웃 추가

        self.setLayout(layout) # 레이아웃 설정


    def previous_result(self):
        global left_button_clicked
        left_button_clicked = True
        self.search_product(-1)

    def next_result(self):
        global right_button_clicked
        right_button_clicked = True
        self.search_product(1)

    def search_product(self, direction=0): # 제품 검색 함수 정의
        global product_id, is_brand, keyword, left_button_clicked, right_button_clicked

        new_keyword = self.search_input.text() # 새로운 검색어 설정
        self.log_output.clear() # 로그 출력 위젯 초기화

        search_results = None # 검색 결과 초기화

        search_url = f'https://kream.co.kr/search?keyword={new_keyword}&tab=products&delivery_method=quick_delivery&sort=popular_score' # 검색 URL 설정
        if new_keyword != keyword: # 새로운 검색어가 이전 검색어와 다를 경우
            self.i = 0 # i를 0으로 설정
            keyword = new_keyword # 검색어 설정
        
        if browser.current_url != search_url: # 현재 URL이 크림 검색 페이지가 아닐 경우
            browser.get(search_url) # 크림 검색 페이지로 이동

        try:
            WebDriverWait(browser, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'body'))) # 로딩 완료 대기

        except TimeoutException : # 시간 초과 발생 시
            self.update_log('검색 결과가 없습니다. (Timeout)') # 검색 결과 없음 메시지 출력
            return
        
        try:
            search_results = WebDriverWait(browser, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="search_result_item product"]'))) # 검색 결과 요소 찾기

        except NoSuchElementException: # 요소 없음 예외 발생 시
            QMessageBox.warning(self, '검색 결과 없음', '검색 결과가 없습니다.')
            return

        except Exception as e: # 그 외의 예외 발생 시
            self.update_log(f'에러발생: {str(e)}')
            return

        self.left_button.setEnabled(False) # 왼쪽 버튼 비활성화
        self.right_button.setEnabled(False) # 오른쪽 버튼 비활성화

        if direction == -1 and self.i > 0:
            self.i -= 1
        elif direction == 1 and self.i < len(search_results) - 1:
            self.i += 1

        if self.i > 0: # i가 0보다 클 경우
            self.left_button.setEnabled(True) # 왼쪽 버튼 활성화


        if self.i < len(search_results) - 1: # i가 검색 결과의 개수보다 작을 경우
            self.right_button.setEnabled(True) # 오른쪽 버튼 활성화

        try:
            result = search_results[self.i] # i 번째 검색 결과 설정

            if result is None: # i 번째 검색 결과가 없을 경우
                QMessageBox.warning(self, '검색 결과 없음', '검색 결과가 없습니다.')
                return
                
            product_name = result.find_element(By.CSS_SELECTOR, 'p[class="name"]').text # 제품 이름 설정
            self.update_log(f'<div style="text-align: center;"><br><b>{product_name}</b>', html=True) # 제품 이름 출력

            product_translated_name = result.find_element(By.CSS_SELECTOR, 'p[class="translated_name"]').text # 제품 한글 이름 설정
            self.update_log(f'<b>{product_translated_name}</b><br></div>', html=True) # 제품 한글 이름 출력

            product_id = result.get_attribute("data-product-id") # 제품 ID 설정
            self.update_log(f'제품 ID: {product_id}') # 제품 ID 출력
            
            amount = result.find_element(By.CSS_SELECTOR, 'p[class="amount"]').text # 제품 가격 설정
            self.update_log(f'즉시구매 가능한 최저가: <b>{amount}</b>', html= True) # 즉시구매가 출력

            image_link = result.find_element(By.CSS_SELECTOR, 'img').get_attribute('src') # 이미지 링크 설정
            image_data = requests.get(image_link).content # 이미지 데이터 설정
            product_pixmap = QPixmap() # 제품 이미지용 QPixmap 객체 생성
            product_pixmap.loadFromData(image_data) # 이미지 데이터 로드

            # Update the image label with the product image
            image_label = self.findChild(QLabel, "image_label") # 이미지 레이블 찾기
            product_pixmap = product_pixmap.scaledToWidth(500) # 이미지 너비 설정
            image_label.setPixmap(product_pixmap) # 이미지 레이블에 제품 이미지 설정
            image_label.setScaledContents(True) # 이미지 레이블에 맞게 이미지 크기 조정

            def format_count(count_str):
                count_str = count_str + '건'
                if '.' in count_str and '만' in count_str:
                    return count_str.replace('.', '').replace('만', ',000').replace('건', '건 이상')
                elif '만' in count_str:
                    return count_str.replace('만', '0,000').replace('건', '건 이상')
                elif ',' in count_str:
                    return count_str.replace(',', '')
                else:
                    return count_str

            try:
                status_value = result.find_element(By.CSS_SELECTOR, 'div[class="status_value"]').text.replace("거래 ", "")
                self.update_log(f'누적 거래량: <b>{format_count(status_value)}</b>', html=True)
            except NoSuchElementException:
                self.update_log('누적 거래량:  <b>0건</b>', html=True)

            wish_figure = result.find_element(By.CSS_SELECTOR, 'span[class="wish_figure"]').text
            self.update_log(f'관심상품 저장수: <b>{format_count(wish_figure)}</b>', html=True)


            review_figure = result.find_element(By.CSS_SELECTOR, 'span[class="review_figure"]').text
            self.update_log(f'스타일 등록수: <b>{format_count(review_figure)}</b>', html=True)
            
            WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로딩 완료 대기
            
            try:
                result.find_element(By.CSS_SELECTOR, 'svg[class="ico-brand-official icon sprite-icons"]') # 브랜드배송 요소 찾기
                self.update_log(f'<br><b><i><div style="text-align: center;">보관판매가 불가능한 브랜드배송 제품입니다. 다시 검색해주세요.<br><br></div></i></b>', html=True) # 브랜드배송 제품 메시지 출력
                is_brand = True # 브랜드배송 여부 설정
                self.search_details_button.setEnabled(False) # 제품 상세정보 버튼 비활성화
                return
            
            except NoSuchElementException: # 요소 없음 예외 발생 시
                pass

            self.search_details_button.setEnabled(True) # 제품 상세정보 버튼 활성화
            self.search_button.setEnabled(False) # 검색 버튼 비활성화

            try:

                if '빠른배송' in result.find_element(By.CSS_SELECTOR, 'div[class="tags"]').text:

            if is_logged_in == True:
                self.start_button.setEnabled(True)

        except NoSuchElementException: # 요소 없음 예외 발생 시
            QMessageBox.warning(self, '요소 없음', '검색 결과가 없습니다.')
            return
        
        except IndexError: # 인덱스 에러 발생 시
            QMessageBox.warning(self, '인덱스에러', '검색 결과가 없습니다.')
            return

        except Exception as e: # 그 외의 예외 발생 시
            QMessageBox.warning(self, '에러 발생', f'{str(e)}')
            return


    def product_details(self):
        browser.get('https://kream.co.kr/products/' + product_id)
        WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로딩 완료 대기
        details = browser.find_elements(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info"]')
        colors = browser.find_element(By.XPATH, '//div[@class="detail-box"]/div[@class="product_info color-target"]').text
        self.update_log(f'발매가: <b>{details[0].text}</b>', html=True)
        self.update_log(f'모델번호: <b>{details[1].text}</b>', html=True)
        self.update_log(f'출시일: <b>{details[2].text}</b>', html=True)
        self.update_log(f'대표색상: <b>{colors}</b>', html=True)

        self.search_button.setEnabled(True)
        self.search_details_button = QPushButton('체결 거래정보', self)
        self.search_details_button.clicked.connect(self.product_sales)
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)
    
    def product_sales(self):
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[class="btn outlinegrey full medium"]'))).click()
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[class="btn btn_size"]'))).click()
        sizes = WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[class="size_item"]')))
        size_items = [size.text for size in sizes]
        selected_size, ok = QInputDialog.getItem(self, '사이즈 선택', '사이즈를 선택하세요.', size_items, 0, False)
        if ok and selected_size:
            for size in sizes:
                if size.text == selected_size:
                    size.click()
                    break
        
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="tab_content show"]')))
        # sales = pd.
    
    @pyqtSlot(str, bool) # PyQt 슬롯 설정
    def update_log(self, message, html=False): # 로그 업데이트 함수 정의
        try:
            self.log_output.moveCursor(QTextCursor.End) # 로그 출력 위젯 커서를 끝으로 이동

            if html: # HTML 형식일 경우
                self.log_output.insertHtml(message + '<br>') # HTML 형식으로 메시지 출력
            else:
                self.log_output.insertPlainText(message + '\n') # 일반 텍스트 형식으로 메시지 출력

        except Exception as e: # 예외 발생 시
            print(f"""[{time.strftime('%H:%M:%S')}]
                  에러 로그:
                  {str(e)}""")
            print(f"""[{time.strftime('%H:%M:%S')}]
                  에러 메세지:
                  {message}""") # 에러 메시지 출력


    def is_valid_email(self, email): # 이메일 유효성 검사 함수 정의
        regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' # 이메일 정규식 설정
        return re.match(regex, email) # 이메일 정규식과 일치하는지 반환


    def is_valid_password(self, password): # 비밀번호 유효성 검사 함수 정의
        has_valid_length = 8 <= len(password) <= 16 # 비밀번호 길이가 8 이상 16 이하인지 확인
        has_letter = re.search(r'[A-Za-z]', password) # 영문자가 포함되어 있는지 확인
        has_number = re.search(r'[0-9]', password) # 숫자가 포함되어 있는지 확인
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>+]', password) # 특수문자가 포함되어 있는지 확인
        return all([has_valid_length, has_letter, has_number, has_special]) # 모든 조건이 참인지 반환


    def login(self, email, pw): # 로그인 함수 정의
        global is_logged_in # 로그인 여부 전역 변수 설정
        browser.get('https://kream.co.kr/login') # 크림 로그인 페이지로 이동

        email_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
        password_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
        email_input.clear() # 이메일 입력 요소 초기화
        email_input.send_keys(email) # 이메일 입력 요소에 이메일 입력
        password_input.clear() # 비밀번호 입력 요소 초기화
        password_input.send_keys(pw) # 비밀번호 입력 요소에 비밀번호 입력
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click() # 로그인 버튼 클릭

        time.sleep(1) # 1초 대기
        toast = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="toast"]'))).text # 토스트 메시지 요소 찾기

        if toast == '이메일 또는 비밀번호를 확인해주세요': # 토스트 메시지가 '이메일 또는 비밀번호를 확인해주세요'일 경우
            QMessageBox.warning(self, '로그인 실패', toast) # 로그인 실패 메시지 출력
            self.email_input.clear() # 이메일 입력 위젯 초기화
            self.pw_input.clear() # 비밀번호 입력 위젯 초기화

        else: # 그 외의 경우
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로그인 완료 대기
            self.update_log(f'크림에 {email} 계정으로 로그인되었습니다.') # 로그인 완료 메시지 출력
            is_logged_in = True # 로그인 여부 설정
            self.email_input.setEnabled(False) # 이메일 입력 위젯 비활성화
            self.pw_input.setEnabled(False) # 비밀번호 입력 위젯 비활성화
            self.login_button.setEnabled(False) # 로그인 버튼 비활성화
        
        if product_id != None:
            self.start_button.setEnabled(True)

        elif is_brand == True:
            self.search_button.setEnabled(False)

    def login_button_clicked(self):
        email = self.email_input.text()
        pw = self.pw_input.text()
        if self.is_valid_email(email):
            if self.is_valid_password(pw):
                self.login(email, pw)
            else:
                QMessageBox.warning(self, "비밀번호 오류", "영문, 숫자, 특수문자를 조합해서 입력해주세요. (8-16자)")
        else:
            QMessageBox.warning(self, "이메일 오류", "이메일 주소를 정확히 입력해주세요.")

    def relogin(self, email, pw): # 다시 로그인 함수 정의
        self.update_log(f'[{time.strftime("%H:%M:%S")}] 로그인 세션이 만료되었습니다. 다시 로그인합니다.') # 로그인 세션 만료 메시지 출력
        
        browser.get('https://kream.co.kr/login') # 로그인 페이지로 이동
        email_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))) # 이메일 입력 요소 찾기
        password_input = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))) # 비밀번호 입력 요소 찾기
        email_input.clear() # 이메일 입력 요소 초기화
        email_input.send_keys(email) # 이메일 입력 요소에 이메일 입력
        password_input.clear() # 비밀번호 입력 요소 초기화
        password_input.send_keys(pw) # 비밀번호 입력 요소에 비밀번호 입력
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click() # 로그인 버튼 클릭
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))) # 로그인 완료 대기
        self.update_log(f'[{time.strftime("%H:%M:%S")}] 크림에 {email} 계정으로 로그인되었습니다.') # 로그인 완료 메시지 출력

    def start_macro(self):
        global sel1, sel2, inventorypage # 선택된 사이즈와 수량, 인벤토리 페이지 URL 전역 변수 설정

        self.left_button.setEnabled(False) # 왼쪽 버튼 비활성화
        self.right_button.setEnabled(False) # 오른쪽 버튼 비활성화
        self.search_details_button.setEnabled(False) # 제품 상세정보 버튼 비활성화

        inventorypage = 'https://kream.co.kr/inventory/' + str(product_id) # 인벤토리 페이지 URL 설정
        browser.get(inventorypage)
        size_options = [] # 사이즈 옵션 리스트 초기화

        try:
            WebDriverWait(browser, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list')))
        
        except TimeoutException:
            QMessageBox.warning(self, '시간초과', '보관판매가 불가능한 제품입니다.\n다시 검색해주세요.')
            return
        
        except: # 그 외의 경우
            self.update_log('인벤토리 페이지 로딩 실패')
            if 'https://kream.co.kr/login' in browser.current_url: # 로그인 페이지로 이동할 경우
                self.relogin(self.email_input.text(), self.pw_input.text())
            return

        finally:
            sizes = browser.find_elements(By.XPATH, '//div[@class="inventory_size_item"]')
            size_options = [f"{sizes[i].text}" for i in range(len(sizes))]

            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                if isinstance(widget, QPushButton) and widget.text().startswith("사이즈"):
                    widget.deleteLater()

            self.size_dropdown.clear()
            self.size_dropdown.addItems(size_options)

        # Show dialog for size and quantity selection  
        dialog = QDialog(self)
        dialog.setWindowTitle('선택')
        layout = QVBoxLayout()

        # Size dropdown
        size_label = QLabel('사이즈:')
        size_combo = QComboBox()
        size_combo.addItems(size_options)
        layout.addWidget(size_label) 
        layout.addWidget(size_combo)

        # Quantity spinbox
        qty_label = QLabel('수량:')
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 100)
        qty_spin.setValue(1)
        layout.addWidget(qty_label)
        layout.addWidget(qty_spin)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        # Show dialog and get result
        if dialog.exec_() == QDialog.Accepted:
            sel1 = size_combo.currentIndex() + 1
            sel2 = qty_spin.value()
            self.update_log(f'선택된 사이즈: {size_options[sel1-1]}')
            self.update_log(f'선택된 수량: {sel2}')
            
            self.search_input.setEnabled(False)
            self.search_button.setEnabled(False)
            self.size_dropdown.setEnabled(False)
            self.start_button.setText('매크로 정지')
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.stop_macro)
            self.is_running = True

            self.update_log(f'\n\n[{time.strftime("%H:%M:%S")}] 매크로 시작')
            self.macro_thread = QThread()
            self.worker = MacroWorker(self.email_input.text(), self.pw_input.text(), sel1, sel2, self.font_size)
            self.worker.moveToThread(self.macro_thread)
            self.macro_thread.started.connect(self.worker.run)
            self.worker.log_message.connect(self.update_log)
            self.macro_thread.start()


    def stop_macro(self):
        global done
        if hasattr(self, 'worker'): # 매크로 워커가 존재할 경우
            self.worker.is_running = False # 실행 여부를 False로 설정
        if hasattr(self, 'macro_thread'): # 매크로 스레드가 존재할 경우
            self.macro_thread.quit() # 매크로 스레드 종료
            self.macro_thread.wait() # 매크로 스레드 대기
        
        done = False
        self.search_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.size_dropdown.setEnabled(True)
        self.search_details_button.setEnabled(True)
        self.left_button.setEnabled(True)
        self.right_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.start_button.setText('매크로 시작')
        self.start_button.clicked.disconnect() 
        self.start_button.clicked.connect(self.start_macro)
        self.is_running = False
        self.update_log(f'[{time.strftime("%H:%M:%S")}] 매크로 정지')


if __name__ == '__main__': # 메인 함수일 경우 (__는 더블 언더스코어, 즉 던더라고 읽음. 역할은 특정 메소드나 변수명을 특별하게 만들어주는 역할)
    try:
        app = QApplication(sys.argv) # QApplication 객체 생성
        font = QFont() # 폰트 객체 생성
        ex = App() # App 객체 생성
        font.setPointSize(ex.font_size) # 폰트 크기 설정
        app.setFont(font) # 어플리케이션 폰트 설정
        print(f"[{time.strftime('%H:%M:%S')}] 프로그램 시작") # 프로그램 시작 메시지 출력
        ex.show() # App 객체 표시
        app.aboutToQuit.connect(lambda: ex.macro_thread.quit() if hasattr(ex, 'macro_thread') else None) # 어플리케이션이 종료될 때 매크로 스레드 종료
        sys.exit(app.exec_()) # 어플리케이션 실행
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 에러발생: {e}")
        input("엔터를 누르면 프로그램이 종료됩니다.")