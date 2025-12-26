#!/usr/bin/env python3
"""
백준 Export - 당일 문제 풀이 + 제출 코드 수집

1. solved.ac API로 당일 푼 문제 찾기 (diff 방식)
2. Playwright로 백준 로그인 후 제출 코드 크롤링
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import requests
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

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
    """백준 문제 풀이 + 코드 수집 (Playwright 사용)"""

    def __init__(self, handle: Optional[str] = None, headless: Optional[bool] = None):
        self.handle = handle or BAEKJOON_HANDLE
        self.headless = headless if headless is not None else SELENIUM_HEADLESS

        if not self.handle:
            raise ValueError("BAEKJOON_HANDLE 환경 변수 필요")

        self.base_url = 'https://solved.ac/api/v3'
        self.cache_file = BAEKJOON_CACHE_PATH
        self.cookies_file = BAEKJOON_COOKIES_PATH
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

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
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                return data.get('problems', [])
        return []

    def save_cache(self, problems: List[int]):
        """문제 목록 캐시 저장"""
        with open(self.cache_file, 'w') as f:
            json.dump({'problems': problems}, f)

    # ============ Playwright 메서드 (코드 크롤링) ============

    def setup_browser(self):
        """Playwright 브라우저 설정"""
        try:
            self.playwright = sync_playwright().start()

            # Chromium 사용 (ARM64에서도 자동 설치됨)
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )

            # Context 생성
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            self.page = self.context.new_page()
            logger.info("Playwright 브라우저 설정 완료")

        except Exception as e:
            raise Exception(f"Playwright 초기화 실패: {e}")

    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"백준 쿠키 저장: {self.cookies_file}")

    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"쿠키 파일 없음: {self.cookies_file}\n"
                "먼저 setup()을 실행하세요"
            )

        with open(self.cookies_file, 'r') as f:
            cookies = json.load(f)

        self.context.add_cookies(cookies)
        logger.info("백준 쿠키 로드 완료")

    def setup(self):
        """최초 1회 설정: 수동 로그인 후 쿠키 저장"""
        self.headless = False
        self.setup_browser()

        logger.info("백준에서 수동 로그인 후 Enter를 눌러주세요...")
        self.page.goto("https://www.acmicpc.net/login")
        input()

        self.save_cookies()
        self.close()
        logger.info("백준 설정 완료")

    def get_my_submissions(self, problem_id: int) -> List[Dict]:
        """특정 문제의 내 제출 목록 가져오기"""
        url = f"https://www.acmicpc.net/status"
        params = {
            'problem_id': problem_id,
            'user_id': self.handle,
            'result_id': 4  # 맞았습니다!!
        }

        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        self.page.goto(f"{url}?{query_string}")
        self.page.wait_for_load_state('networkidle')

        submissions = []

        try:
            # 제출 테이블에서 첫 번째 정답 찾기
            rows = self.page.locator("#status-table tbody tr").all()[:5]  # 최대 5개만 확인

            for row in rows:
                cols = row.locator("td").all()

                if len(cols) >= 7:
                    submission_id = cols[0].inner_text()
                    language = cols[6].inner_text()
                    code_length = cols[4].inner_text()
                    memory = cols[3].inner_text()
                    time_ms = cols[2].inner_text()

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
            self.page.goto(url)
            self.page.wait_for_load_state('networkidle')

            # 코드 영역 찾기
            code_element = self.page.locator("textarea.form-control").first
            code = code_element.input_value()
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
                self.setup_browser()
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

                self.close()

            except FileNotFoundError:
                logger.warning("백준 쿠키 없음 - 코드 수집 건너뜀")
                logger.warning("'setup()' 실행 후 재시도하세요")
            except Exception as e:
                logger.error(f"코드 크롤링 실패: {e}")
                self.close()

        # 캐시 업데이트
        self.save_cache(current_problems)

        return solved_today

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
