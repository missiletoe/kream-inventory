from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QSpinBox, QDialogButtonBox
from PyQt6.QtCore import QThread, Qt
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime, timedelta
import re
from login import LoginManager


class MacroWorker(QObject):
    log_message = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, browser, email, password, size, qty, click_term):
        super().__init__()
        self.browser = browser
        self.email = email
        self.password = password
        self.size = size
        self.qty = qty
        self.click_term = click_term
        self.is_running = True
        self.login_manager = LoginManager(browser=self.browser)

    def run(self, count=0, inventory_opened=False):
        self.is_running = True
        self.log_message.emit("\n\n매크로 실행 중...")

        while self.is_running:

            try:

                # 로그인이 풀려서 로그인 페이지로 빠졌을 경우, 재로그인
                if 'login' in self.browser.current_url:
                    self.login_manager.relogin(self.email, self.password)
                    return

                # 엉뚱한 페이지로 빠졌을 경우, 뒤로가기 후 재시도
                elif 'inventory' not in self.browser.current_url:
                    self.browser.back()
                    WebDriverWait(self.browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                    return

                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.inventory_size_list'))
                )

                input_box = self.browser.find_element(
                    By.CSS_SELECTOR, f'div.inventory_size_item:nth-child({self.size}) input'
                )

                input_box.clear()
                input_box.send_keys(str(self.qty))

                complete_button = WebDriverWait(self.browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.complete_btn_box'))
                )
                complete_button.click()

                count += 1
                self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] {count}회 시도')

                try:
                    if '안쪽 라벨 사이즈' in self.browser.find_element(By.CSS_SELECTOR, 'div.layer_container').text:
                        example_boxes = WebDriverWait(self.browser, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.example_box.label')))
                        for label in example_boxes:
                            label.click()
                        WebDriverWait(self.browser, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn.solid.full.large'))).click()
                except NoSuchElementException:
                    pass

                popup = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.toast')))
                time.sleep(1)

                if 'show' in popup.get_attribute('class'):
                    self.log_message.emit(f'{popup.text}') 

                    if popup.text == '신규 보관신청이 제한된 카테고리의 상품입니다.':
                        time.sleep(self.click_term - 1)
                        return

                    elif popup.text == '상대방의 입찰 삭제, 카드사 응답실패 등 예상치 못한 오류로 인해 계속 진행할 수 없습니다. 이전 단계로 돌아갑니다.' or popup.text == '인터넷, 와이파이, 모바일 데이터 혹은 비행기모드 설정을 확인해 주시기 바랍니다.':
                        block_time = datetime.now() + timedelta(seconds=(3600 - self.click_term * 200))
                        self.log_message.emit(f'[{time.strftime("%H:%M:%S")} ~ {block_time.strftime("%H:%M:%S")}] 매크로 중단')
                        
                        # [ 3600초(1시간) - (클릭 텀 * 200번) ] 대기
                        time.sleep(3600 - self.click_term * 200)
                        
                        self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 매크로 재시작')
                        count = 0
                        self.browser.refresh()
                        return
                
                # 다음 페이지로 이동되었거나, 팝업이 사라졌거나, 로그인이 풀린 경우
                else:
                    
                    try:
                        WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

                        # 인벤토리 페이지 열림 여부 설정
                        if self.browser.find_element(By.CSS_SELECTOR, 'span.title_txt').text == '신청내역':
                            inventory_opened = True

                        # 보증금 결제하기 버튼 클릭
                        self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 보증금 결제 진행 중...')
                        purchase_button = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.display_button')))
                        if purchase_button.get_attribute('class') == 'display_button large dark_filled active block bold':
                            purchase_button.click()
                        else:
                            continue

                        # 모달 창이 나타날 때까지 대기
                        modal_container = WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.layer_container'
                                                            ))
                        )
                        if modal_container == None:
                            continue

                        # 모달 창의 체크박스 요소 클릭
                        modal_checkboxes = WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.section-item.display_item.empty_header'))
                        )
                        checkbox_labels = modal_checkboxes.find_elements(By.CSS_SELECTOR, 'div.title-description-checkbox.line label')
                        for label in checkbox_labels:
                            label.click()

                        # 최종 보증금 결제하기 버튼 클릭
                        purchase_button_final = modal_container.find_element(By.CSS_SELECTOR, 'div.layer_bottom div.bottom-button button')
                        if purchase_button_final.get_attribute('class') == 'display_button large dark_filled active block bold':
                            purchase_button_final.click()
                        else:
                            continue

                        try:
                            # 이상한 페이지 요소 찾기
                            service_error = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.info_txt'))).text
                            if service_error == '일시적인 서비스 장애 입니다.':
                                self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 일시적인 서비스 장애입니다. 다시 시도합니다.')
                                count = 0
                                self.browser.refresh()
                                return
                                
                        except:
                            pass

                        try:
                            popup = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.toast.sm.show"]')))
                            self.log_message.emit(f'{popup.text}')
                            self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 보증금 결제 실패. 다시 시도합니다.')
                            inventory_opened = False
                            self.browser.refresh()
                            count = 0
                            time.sleep(self.click_term - 1)
                        except:
                            self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 보관판매 신청 성공!')
                            self.is_running = False
                            break

                    except Exception as e:
                        self.log_message.emit(f'[{time.strftime("%H:%M:%S")}] 오류 발생: {str(e)}. 다시 시도합니다.')
                        count = 0
                        if inventory_opened == True:
                            inventory_opened = False
                            self.browser.refresh()
                        time.sleep(self.click_term - 1)
                        continue

            except Exception as e:
                self.log_message.emit("매크로 실행 중 오류 발생: " + str(e))

            # click_term 초마다 반복 (1초씩 체크하며 중단 여부 확인)
            for _ in range(self.click_term):
                if not self.is_running:
                    break
                time.sleep(1)

        self.finished.emit()


def start_macro(ui):
    # 제품 정보 확인
    product_info_text = ui.product_info.toPlainText().strip()
    if not product_info_text:
        ui.log_output.append('제품 정보를 먼저 선택해주세요.')
        return
    match = re.search(r'\[(\d+)\]', product_info_text)
    if match:
        product_id = match.group(1)
    else:
        ui.log_output.append('제품 ID를 추출할 수 없습니다.')
        return
    inventorypage = f'https://kream.co.kr/inventory/{product_id}'
    ui.browser.get(inventorypage)

    try:
        WebDriverWait(ui.browser, 15).until(lambda b: b.find_element(By.CSS_SELECTOR, 'div.inventory_size_list'))
    except TimeoutException:
        ui.log_output.append('인벤토리 페이지 로딩 실패')
        return

    sizes = ui.browser.find_elements(By.XPATH, '//div[@class="inventory_size_item"]')
    size_options = [s.text for s in sizes]

    dialog = QDialog(ui)
    dialog.setWindowTitle('선택')
    layout = QVBoxLayout()

    size_label = QLabel('사이즈:')
    layout.addWidget(size_label)
    size_combo = QComboBox()
    size_combo.addItems(size_options)
    layout.addWidget(size_combo)

    qty_label = QLabel('수량:')
    layout.addWidget(qty_label)
    qty_spin = QSpinBox()
    qty_spin.setRange(1, 100)
    qty_spin.setValue(1)
    layout.addWidget(qty_spin)

    click_term_label = QLabel('보관판매시도 주기 (초단위):')
    layout.addWidget(click_term_label)
    click_term_combo = QComboBox()
    click_term_options = [str(i) for i in range(8, 19)]
    click_term_combo.addItems(click_term_options)
    click_term_combo.setCurrentIndex(len(click_term_options) - 1)
    layout.addWidget(click_term_combo)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, Qt.Orientation.Horizontal)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.setLayout(layout)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    sel_index = size_combo.currentIndex() + 1  # 1-indexed
    qty = qty_spin.value()
    click_term = int(click_term_combo.currentText())

    ui.log_output.append(f'[{time.strftime("%H:%M:%S")}] 매크로 시작')
    ui.log_output.append(f'{size_options[sel_index - 1]} 사이즈 {qty}개')
    ui.log_output.append(f'{click_term}초마다 한번 시도')

    ui.search_input.setEnabled(False)
    ui.search_button.setEnabled(False)
    ui.search_details_button.setEnabled(False)
    ui.left_button.setEnabled(False)
    ui.right_button.setEnabled(False)

    ui.start_button.setText('매크로 정지')
    ui.start_button.clicked.disconnect()
    ui.start_button.clicked.connect(lambda: stop_macro(ui))

    ui.macro_thread = QThread()
    ui.worker = MacroWorker(ui.browser, ui.email_input.text(), ui.pw_input.text(), sel_index, qty, click_term)
    ui.worker.moveToThread(ui.macro_thread)
    ui.macro_thread.started.connect(ui.worker.run)
    ui.worker.log_message.connect(ui.log_output.append)
    ui.worker.finished.connect(lambda: stop_macro(ui))
    ui.macro_thread.start()

def stop_macro(ui):

    if hasattr(ui, 'worker'):
        ui.worker.is_running = False
        ui.worker.finished.disconnect()

    if hasattr(ui, 'macro_thread'):
        ui.macro_thread.quit()
        ui.macro_thread.wait()

    ui.search_input.setEnabled(True)
    ui.search_button.setEnabled(True)
    ui.search_details_button.setEnabled(True)
    ui.left_button.setEnabled(True)
    ui.right_button.setEnabled(True)
    ui.start_button.setText('매크로 시작')
    ui.start_button.clicked.disconnect()
    ui.start_button.clicked.connect(lambda: start_macro(ui))
    ui.log_output.append(f'[{time.strftime("%H:%M:%S")}] 매크로 종료')

    if hasattr(ui, 'worker'):
        del ui.worker