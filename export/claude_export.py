#!/usr/bin/env python3
"""
Claude Export 자동화

Selenium을 사용하여 claude.ai에서 대화 Export를 자동으로 다운로드합니다.
"""

import time
import pickle
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ClaudeExporter:
    """Claude.ai Export 자동화"""
    
    def __init__(self, headless=True, download_dir=None):
        self.headless = headless
        self.cookies_file = Path.home() / ".claude_cookies.pkl"
        self.download_dir = Path(download_dir) if download_dir else Path.home() / "Downloads"
        self.driver = None
    
    def setup_driver(self):
        """Selenium WebDriver 설정"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux aarch64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
    
    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"✅ 쿠키 저장: {self.cookies_file}")
    
    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"쿠키 파일 없음: {self.cookies_file}\n"
                "먼저 setup()을 실행하세요"
            )
        
        with open(self.cookies_file, 'rb') as f:
            cookies = pickle.load(f)
        
        self.driver.get("https://claude.ai")
        time.sleep(2)
        
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception:
                pass
    
    def setup(self):
        """최초 1회 설정: 수동 로그인 후 쿠키 저장"""
        self.headless = False
        self.setup_driver()
        
        print("브라우저에서 수동 로그인 후 Enter를 눌러주세요...")
        self.driver.get("https://claude.ai/login")
        input()
        
        self.save_cookies()
        self.driver.quit()
        print("✅ 설정 완료")
    
    def export(self):
        """Export 실행 후 ZIP 파일 경로 반환"""
        self.setup_driver()
        self.load_cookies()
        
        self.driver.get("https://claude.ai")
        time.sleep(3)
        
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            print("❌ 로그인 실패")
            self.driver.quit()
            return None
        
        self.driver.get("https://claude.ai/settings/account")
        time.sleep(3)
        
        try:
            privacy_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), 'Privacy')]")
                )
            )
            privacy_link.click()
            time.sleep(2)
        except:
            print("⚠️ Privacy 탭을 찾을 수 없습니다")
        
        try:
            export_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, 
                     "//button[contains(text(), 'Export') or "
                     "contains(text(), 'export')]")
                )
            )
            export_button.click()
            
            time.sleep(30)
            
            zip_files = list(self.download_dir.glob("conversations*.zip"))
            if zip_files:
                latest = max(zip_files, key=lambda p: p.stat().st_mtime)
                print(f"✅ Export 완료: {latest}")
                return str(latest)
            else:
                print("⚠️ ZIP 파일을 찾을 수 없습니다")
                return None
                
        except Exception as e:
            print(f"❌ Export 실패: {e}")
            return None
        
        finally:
            self.driver.quit()


if __name__ == '__main__':
    import sys
    
    exporter = ClaudeExporter(headless=True)
    
    if "--setup" in sys.argv:
        exporter.setup()
    else:
        zip_path = exporter.export()
        if zip_path:
            print(f"다운로드: {zip_path}")
