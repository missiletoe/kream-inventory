import os
import stat
from dotenv import load_dotenv
from webdriver_manager.chrome import ChromeDriverManager

# .env 파일 로드
load_dotenv()

class Config:
    LOGIN_URL = "https://kream.co.kr/login"
    INVENTORY_URL = lambda product_id: f"https://kream.co.kr/inventory/{product_id}"

    # ✅ WebDriverManager에서 chromedriver 실행 경로 명확하게 설정
    CHROME_DRIVER_PATH = os.path.join(os.path.dirname(ChromeDriverManager().install()), "chromedriver")
        
    # ✅ chromedriver 실행 권한 부여
    if os.path.exists(CHROME_DRIVER_PATH):
        os.chmod(CHROME_DRIVER_PATH, stat.S_IRWXU)  # 소유자 실행 권한 추가