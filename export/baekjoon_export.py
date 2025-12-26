#!/usr/bin/env python3
"""
백준 Export - 당일 문제 풀이 + 제출 코드 수집

1. solved.ac API로 당일 푼 문제 찾기 (diff 방식)
2. Selenium으로 백준 로그인 후 제출 코드 크롤링
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import pickle
import logging
import requests
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import (
    BAEKJOON_HANDLE,
    BAEKJOON_COOKIES_PATH,
    BAEKJOON_CACHE_PATH,
    SELENIUM_HEADLESS,
    get_log_file
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('baekjoon_export')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaekjoonExporter:
    """백준 문제 풀이 + 코드 수집"""

    def __init__(self, handle: Optional[str] = None, headless: Optional[bool] = None):
        self.handle = handle or BAEKJOON_HANDLE
        self.headless = headless if headless is not None else SELENIUM_HEADLESS

        if not self.handle:
            raise ValueError("BAEKJOON_HANDLE 환경 변수 필요")

        self.base_url = 'https://solved.ac/api/v3'
        self.cache_file = BAEKJOON_CACHE_PATH
        self.cookies_file = BAEKJOON_COOKIES_PATH
        self.driver = None
    
    # ============ solved.ac API 메서드 (기존 유지) ============
    
    def get_user_info(self) -> Dict:
        """사용자 정보 가져오기"""
        url = f"{self.base_url}/user/show"
        params = {'handle': self.handle}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_solved_problems(self) -> List[int]:
        """사용자가 푼 모든 문제 번호 가져오기"""
        problems = []
        page = 1
        
        while True:
            url = f"{self.base_url}/search/problem"
            params = {
                'query': f'solved_by:{self.handle}',
                'page': page,
                'sort': 'id',
                'direction': 'asc'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data['items']:
                break
            
            for item in data['items']:
                problems.append(item['problemId'])
            
            page += 1
        
        return problems
    
    def get_problem_info(self, problem_id: int) -> Dict:
        """문제 상세 정보 가져오기"""
        url = f"{self.base_url}/problem/show"
        params = {'problemId': problem_id}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            'problem_id': data['problemId'],
            'title': data['titleKo'],
            'level': data['level'],
            'tier': self._level_to_tier(data['level']),
            'tags': [tag['displayNames'][0]['name'] for tag in data['tags']],
            'url': f"https://www.acmicpc.net/problem/{data['problemId']}"
        }
    
    def _level_to_tier(self, level: int) -> str:
        """레벨 숫자를 티어 문자열로 변환"""
        tiers = [
            'Unrated',
            'Bronze V', 'Bronze IV', 'Bronze III', 'Bronze II', 'Bronze I',
            'Silver V', 'Silver IV', 'Silver III', 'Silver II', 'Silver I',
            'Gold V', 'Gold IV', 'Gold III', 'Gold II', 'Gold I',
            'Platinum V', 'Platinum IV', 'Platinum III', 'Platinum II', 'Platinum I',
            'Diamond V', 'Diamond IV', 'Diamond III', 'Diamond II', 'Diamond I',
            'Ruby V', 'Ruby IV', 'Ruby III', 'Ruby II', 'Ruby I'
        ]
        
        if 0 <= level < len(tiers):
            return tiers[level]
        return 'Unknown'
    
    def load_cache(self) -> List[int]:
        """캐시된 문제 목록 로드"""
        if not self.cache_file.exists():
            return []
        
        with open(self.cache_file, 'r') as f:
            data = json.load(f)
            return data.get('problems', [])
    
    def save_cache(self, problems: List[int]):
        """문제 목록 캐시 저장"""
        with open(self.cache_file, 'w') as f:
            json.dump({'problems': problems}, f)
    
    # ============ Selenium 메서드 (코드 크롤링) ============
    
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

        # Raspberry Pi의 경우 환경에 따라 Chromium 경로 자동 감지
        import platform
        import os
        if platform.machine() == 'aarch64' or platform.machine() == 'armv7l':
            # Raspberry Pi에서 chromium 경로 확인
            chromium_paths = [
                '/snap/bin/chromium',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium'
            ]
            for chromium_path in chromium_paths:
                if os.path.exists(chromium_path):
                    options.binary_location = chromium_path
                    logger.info(f"Chromium 경로 설정: {chromium_path}")
                    break

        try:
            # Selenium Manager가 자동으로 chromedriver 관리
            self.driver = webdriver.Chrome(options=options)
            logger.info("Selenium WebDriver 초기화 완료")
        except Exception as e:
            raise Exception(f"WebDriver 초기화 실패: {e}")
    
    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info(f"백준 쿠키 저장: {self.cookies_file}")
    
    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"쿠키 파일 없음: {self.cookies_file}\n"
                "먼저 setup()을 실행하세요"
            )
        
        with open(self.cookies_file, 'rb') as f:
            cookies = pickle.load(f)
        
        self.driver.get("https://www.acmicpc.net")
        import time
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

        logger.info("백준에서 수동 로그인 후 Enter를 눌러주세요...")
        self.driver.get("https://www.acmicpc.net/login")
        input()

        self.save_cookies()
        self.driver.quit()
        logger.info("백준 설정 완료")
    
    def get_my_submissions(self, problem_id: int) -> List[Dict]:
        """특정 문제의 내 제출 목록 가져오기"""
        url = f"https://www.acmicpc.net/status"
        params = {
            'problem_id': problem_id,
            'user_id': self.handle,
            'result_id': 4  # 맞았습니다!!
        }
        
        self.driver.get(url + '?' + '&'.join(f'{k}={v}' for k, v in params.items()))
        
        import time
        time.sleep(2)
        
        submissions = []
        
        try:
            # 제출 테이블에서 첫 번째 정답 찾기
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#status-table tbody tr")
            
            for row in rows[:5]:  # 최대 5개만 확인
                cols = row.find_elements(By.TAG_NAME, "td")
                
                if len(cols) >= 7:
                    submission_id = cols[0].text
                    language = cols[6].text
                    code_length = cols[4].text
                    memory = cols[3].text
                    time_ms = cols[2].text
                    
                    submissions.append({
                        'submission_id': submission_id,
                        'language': language,
                        'code_length': code_length,
                        'memory': memory,
                        'time': time_ms
                    })
        
        except Exception as e:
            logger.warning(f"제출 목록 가져오기 실패: {e}")
        
        return submissions
    
    def get_source_code(self, submission_id: str) -> str:
        """제출 코드 가져오기"""
        url = f"https://www.acmicpc.net/source/{submission_id}"
        
        try:
            self.driver.get(url)
            
            import time
            time.sleep(1)
            
            # 코드 영역 찾기
            code_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.form-control"))
            )
            
            code = code_element.get_attribute('value')
            return code
        
        except Exception as e:
            logger.warning(f"코드 가져오기 실패: {e}")
            return ""
    
    # ============ 통합 Export 메서드 ============
    
    def export_today(self) -> List[Dict]:
        """당일 푼 문제 + 제출 코드 수집"""
        logger.info(f"{self.handle}의 오늘 문제 풀이 수집 중...")

        # 1. solved.ac로 오늘 푼 문제 찾기
        current_problems = self.get_solved_problems()
        logger.info(f"총 {len(current_problems)}개 문제 해결")

        cached_problems = self.load_cache()
        new_problems = set(current_problems) - set(cached_problems)

        if not new_problems:
            logger.info("오늘 푼 새로운 문제 없음")
            self.save_cache(current_problems)
            return []

        logger.info(f"새로운 문제 {len(new_problems)}개 발견")

        # 2. 각 문제의 상세 정보 수집
        solved_today = []
        for problem_id in sorted(new_problems):
            try:
                info = self.get_problem_info(problem_id)
                solved_today.append(info)
                logger.info(f"{problem_id}: {info['title']} ({info['tier']})")
            except Exception as e:
                logger.warning(f"{problem_id}: 정보 수집 실패 - {e}")
        
        # 3. 제출 코드 크롤링 (선택적)
        if solved_today:
            try:
                logger.info("제출 코드 크롤링 시작...")
                self.setup_driver()
                self.load_cookies()

                for problem in solved_today:
                    problem_id = problem['problem_id']

                    # 제출 목록 가져오기
                    submissions = self.get_my_submissions(problem_id)

                    if submissions:
                        # 가장 최근 정답 코드 가져오기
                        latest = submissions[0]
                        code = self.get_source_code(latest['submission_id'])

                        if code:
                            problem['submission'] = {
                                'submission_id': latest['submission_id'],
                                'language': latest['language'],
                                'code': code,
                                'memory': latest['memory'],
                                'time': latest['time']
                            }
                            logger.info(f"  코드 수집 완료 ({latest['language']})")
                        else:
                            logger.warning(f"  코드 수집 실패")
                    else:
                        logger.warning(f"  제출 내역 없음")

                self.driver.quit()

            except FileNotFoundError:
                logger.warning("백준 쿠키 없음 - 코드 수집 건너뜀")
                logger.warning("'setup()' 실행 후 재시도하세요")
            except Exception as e:
                logger.error(f"코드 크롤링 실패: {e}")
                if self.driver:
                    self.driver.quit()
        
        # 캐시 업데이트
        self.save_cache(current_problems)
        
        return solved_today


if __name__ == '__main__':
    import sys
    
    exporter = BaekjoonExporter()
    
    if "--setup" in sys.argv:
        exporter.setup()
    else:
        problems = exporter.export_today()
        
        for p in problems:
            print(f"\n[{p['tier']}] {p['problem_id']}: {p['title']}")
            if 'submission' in p:
                print(f"  언어: {p['submission']['language']}")
                print(f"  메모리: {p['submission']['memory']}")
                print(f"  시간: {p['submission']['time']}")
                print(f"  코드 길이: {len(p['submission']['code'])}자")
