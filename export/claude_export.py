#!/usr/bin/env python3
"""
Claude Export 자동화

Playwright를 사용하여 claude.ai에서 대화 Export를 자동으로 다운로드합니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth_sync

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
    """Claude.ai Export 자동화 (Playwright 사용)"""

    def __init__(self, headless=None, download_dir=None):
        self.headless = headless if headless is not None else SELENIUM_HEADLESS
        self.cookies_file = CLAUDE_COOKIES_PATH
        self.download_dir = Path(download_dir) if download_dir else CLAUDE_DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        logger.info(f"ClaudeExporter 초기화: download_dir={self.download_dir}")

    def setup_browser(self):
        """Playwright 브라우저 설정"""
        try:
            self.playwright = sync_playwright().start()

            # Chromium 사용 (ARM64에서도 자동 설치됨)
            # Cloudflare 우회를 위한 추가 설정
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled'  # 자동화 감지 비활성화
                ]
            )

            # Context 생성 (Cloudflare 우회 설정)
            # 영구 사용자 프로필 사용 (Cloudflare trust 유지)
            import os
            user_data_dir = os.path.expanduser('~/.playwright-browsers/claude-profile')
            os.makedirs(user_data_dir, exist_ok=True)

            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                accept_downloads=True,
                locale='en-US',
                timezone_id='America/New_York',
                storage_state=user_data_dir + '/state.json' if os.path.exists(user_data_dir + '/state.json') else None,
                # Cloudflare 우회를 위한 추가 헤더
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )

            self.page = self.context.new_page()

            # playwright-stealth 적용 (Cloudflare Turnstile 우회)
            stealth_sync(self.page)

            logger.info("Playwright 브라우저 설정 완료 (Stealth mode)")

        except Exception as e:
            raise Exception(f"Playwright 초기화 실패: {e}")

    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"쿠키 저장: {self.cookies_file}")

    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"쿠키 파일 없음: {self.cookies_file}\n"
                "먼저 setup()을 실행하세요 (python -m export.claude_export --setup)"
            )

        with open(self.cookies_file, 'r') as f:
            cookies = json.load(f)

        self.context.add_cookies(cookies)
        logger.info("쿠키 로드 완료")

    def setup(self):
        """최초 1회 설정: 수동 로그인 후 쿠키 저장"""
        self.headless = False
        self.setup_browser()

        logger.info("브라우저에서 수동 로그인을 진행하세요...")
        self.page.goto("https://claude.ai/login", wait_until='networkidle')

        # Cloudflare Turnstile 자동 대기 (최대 30초)
        try:
            logger.info("Cloudflare 체크 대기 중...")
            self.page.wait_for_selector("body", timeout=30000, state='visible')
            # Turnstile iframe이 사라질 때까지 대기
            self.page.wait_for_function(
                "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
                timeout=30000
            )
            logger.info("Cloudflare 체크 통과")
        except Exception as e:
            logger.warning(f"Cloudflare 대기 실패: {e}")

        time.sleep(2)
        input("로그인 완료 후 Enter를 눌러주세요...")

        # 쿠키 + 브라우저 상태 저장 (Cloudflare trust 포함)
        self.save_cookies()

        # 브라우저 상태 저장 (localStorage, sessionStorage 등)
        import os
        user_data_dir = os.path.expanduser('~/.playwright-browsers/claude-profile')
        os.makedirs(user_data_dir, exist_ok=True)
        self.context.storage_state(path=user_data_dir + '/state.json')
        logger.info(f"브라우저 상태 저장: {user_data_dir}/state.json")

        self.close()
        logger.info("설정 완료")

    def export(self):
        """Export 실행 후 ZIP 파일 경로 반환"""
        logger.info("Claude Export 시작...")
        self.setup_browser()
        self.load_cookies()

        self.page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)

        # 스크린샷 저장 (디버깅용)
        screenshot_path = PROJECT_ROOT / 'temp' / 'claude_export_screenshot.png'
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(screenshot_path))
        logger.info(f"스크린샷 저장: {screenshot_path}")

        try:
            # 로그인 확인 (Cloudflare 또는 로그인 페이지 체크)
            self.page.wait_for_selector("body", timeout=10000)

            # Cloudflare 체크 대기
            try:
                self.page.wait_for_function(
                    "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
                    timeout=60000
                )
                logger.info("Cloudflare 체크 통과")
            except:
                logger.warning("Cloudflare 대기 타임아웃 (계속 진행)")

            logger.info("페이지 로드 완료")
        except:
            logger.error("페이지 로드 실패")
            self.close()
            return None

        # Settings 페이지로 이동
        self.page.goto("https://claude.ai/settings/account", wait_until='domcontentloaded', timeout=60000)

        # 스크린샷 저장
        screenshot_path2 = PROJECT_ROOT / 'temp' / 'claude_settings_screenshot.png'
        self.page.screenshot(path=str(screenshot_path2))
        logger.info(f"Settings 페이지 스크린샷: {screenshot_path2}")

        try:
            # Privacy 탭 클릭
            privacy_link = self.page.locator("a:has-text('Privacy'), a[href*='privacy']").first
            privacy_link.click()
            self.page.wait_for_timeout(2000)
            logger.info("Privacy 탭 이동")
        except Exception as e:
            logger.warning(f"Privacy 탭 찾기 실패: {e}")

        try:
            # Export 버튼 클릭 및 다운로드 대기
            with self.page.expect_download(timeout=60000) as download_info:
                export_button = self.page.locator("button:has-text('Export'), button:has-text('export'), button:has-text('Download')").first
                export_button.click()
                logger.info("Export 버튼 클릭")

            download = download_info.value

            # 다운로드 파일 저장
            save_path = self.download_dir / download.suggested_filename
            download.save_as(save_path)
            logger.info(f"Export 완료: {save_path}")

            return str(save_path)

        except Exception as e:
            logger.error(f"Export 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self.close()

    def close(self):
        """브라우저 종료"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


if __name__ == '__main__':
    import sys

    exporter = ClaudeExporter()  # headless는 settings.py에서 설정

    if "--setup" in sys.argv:
        exporter.setup()
    else:
        zip_path = exporter.export()
        if zip_path:
            print(f"다운로드: {zip_path}")
