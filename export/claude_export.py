#!/usr/bin/env python3
"""
Claude Export 자동화

Selenium을 사용하여 claude.ai에서 대화 Export를 자동으로 다운로드합니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import pickle
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import (
    CLAUDE_COOKIES_PATH,
    CLAUDE_DOWNLOAD_DIR,
    SELENIUM_HEADLESS,
    SELENIUM_TIMEOUT,
    get_log_file
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_export')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeExporter:
    """Claude.ai Export 자동화"""

    def __init__(self, headless=None, download_dir=None):
        self.headless = headless if headless is not None else SELENIUM_HEADLESS
        self.cookies_file = CLAUDE_COOKIES_PATH
        self.download_dir = Path(download_dir) if download_dir else CLAUDE_DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None
        logger.info(f"ClaudeExporter 초기화: download_dir={self.download_dir}")

    def setup_driver(self):
        """Selenium WebDriver 설정"""
        options = Options()

        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-software-rasterizer")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
        }
        options.add_experimental_option("prefs", prefs)

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Chromium 브라우저 경로 설정 (라즈베리파이 snap 버전)
        options.binary_location = "/snap/bin/chromium"

        # chromedriver 경로 시도
        driver_paths = [
            None,  # 자동 감지
            '/usr/bin/chromedriver',
            '/usr/lib/chromium-browser/chromedriver'
        ]

        for path in driver_paths:
            try:
                if path:
                    service = Service(path)
                    self.driver = webdriver.Chrome(service=service, options=options)
                else:
                    self.driver = webdriver.Chrome(options=options)
                break
            except Exception as e:
                if path == driver_paths[-1]:
                    raise Exception(f"chromedriver를 찾을 수 없습니다: {e}")
                continue

        logger.info("WebDriver 설정 완료")

    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info(f"쿠키 저장: {self.cookies_file}")

    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"쿠키 파일 없음: {self.cookies_file}\n"
                "먼저 setup()을 실행하세요 (python -m export.claude_export --setup)"
            )

        with open(self.cookies_file, 'rb') as f:
            cookies = pickle.load(f)

        self.driver.get("https://claude.ai")
        time.sleep(2)

        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"쿠키 추가 실패 (무시): {e}")

        logger.info("쿠키 로드 완료")

    def setup(self):
        """최초 1회 설정: 수동 로그인 후 쿠키 저장"""
        self.headless = False
        self.setup_driver()

        logger.info("브라우저에서 수동 로그인을 진행하세요...")
        self.driver.get("https://claude.ai/login")
        input("로그인 완료 후 Enter를 눌러주세요...")

        self.save_cookies()
        self.driver.quit()
        logger.info("설정 완료")

    def export(self):
        """Export 실행 후 ZIP 파일 경로 반환"""
        logger.info("Claude Export 시작...")
        self.setup_driver()
        self.load_cookies()

        self.driver.get("https://claude.ai")
        time.sleep(3)

        try:
            # 로그인 확인
            WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("로그인 확인 완료")
        except:
            logger.error("로그인 실패")
            self.driver.quit()
            return None

        # Settings 페이지로 이동
        self.driver.get("https://claude.ai/settings/account")
        time.sleep(3)

        try:
            # Privacy 탭 클릭
            privacy_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), 'Privacy') or contains(@href, 'privacy')]")
                )
            )
            privacy_link.click()
            time.sleep(2)
            logger.info("Privacy 탭 이동")
        except Exception as e:
            logger.warning(f"Privacy 탭 찾기 실패: {e}")

        try:
            # Export 버튼 클릭
            export_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(., 'Export') or contains(., 'export') or contains(., 'Download')]")
                )
            )
            export_button.click()
            logger.info("Export 버튼 클릭")

            # ZIP 파일 다운로드 대기
            time.sleep(30)

            zip_files = list(self.download_dir.glob("conversations*.zip"))
            if zip_files:
                latest = max(zip_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"Export 완료: {latest}")
                return str(latest)
            else:
                logger.warning("ZIP 파일을 찾을 수 없습니다")
                return None

        except Exception as e:
            logger.error(f"Export 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self.driver.quit()


if __name__ == '__main__':
    import sys

    exporter = ClaudeExporter(headless=False)  # 테스트 시 headless=False

    if "--setup" in sys.argv:
        exporter.setup()
    else:
        zip_path = exporter.export()
        if zip_path:
            print(f"다운로드: {zip_path}")
