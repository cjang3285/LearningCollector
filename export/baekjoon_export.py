#!/usr/bin/env python3
"""
백준 Export - 백준허브 연동 레포에서 백준 제출 수집

백준허브와 연동된 레포지터리의 백준 폴더에서 당일 제출된 문제를 수집합니다.
백준허브 크롬 확장 프로그램이 자동으로 푸시한 커밋을 읽어옵니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
import requests
from datetime import datetime, timezone, date
from typing import List, Dict, Optional

from config.settings import GITHUB_TOKEN, GITHUB_USERNAMES, get_log_file

# provide legacy name for backwards-compatible patching/tests
GITHUB_USERNAME = GITHUB_USERNAMES[0] if GITHUB_USERNAMES else None

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
    """백준허브 연동 레포 기반 문제 풀이 수집"""

    def __init__(
        self,
        baekjoon_repo: str = "Baekjoon_solutions",
        username: Optional[str] = None,
        token: Optional[str] = None
    ):
        """
        Args:
            baekjoon_repo: 백준허브와 연동된 레포지터리 이름 (기본값: Baekjoon_solutions)
            username: GitHub 사용자명
            token: GitHub Personal Access Token
        """
        # Prefer list-based config; use first username as primary if provided
        primary = GITHUB_USERNAMES[0] if GITHUB_USERNAMES else None
        self.username = username or primary
        self.token = token or GITHUB_TOKEN
        self.baekjoon_repo = baekjoon_repo

        if not self.username or not self.token:
            raise ValueError("GITHUB 사용자(primary)와 GITHUB_TOKEN 환경 변수 필요")

        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        logger.info(f"BaekjoonExporter 초기화: {self.username}/{self.baekjoon_repo}")

    def get_commits(self, since: datetime, until: datetime) -> List[Dict]:
        """
        특정 기간의 커밋 가져오기

        Args:
            since: 시작 시간 (timezone aware)
            until: 종료 시간 (timezone aware)

        Returns:
            커밋 리스트
        """
        url = f"{self.base_url}/repos/{self.username}/{self.baekjoon_repo}/commits"
        params = {
            'since': since.isoformat(),
            'until': until.isoformat(),
            'per_page': 100
        }
        logger.info(f"커밋 가져오기: url='{url}', params={params}")

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        commits = response.json()
        logger.info(f"백준허브 연동 레포에서 {len(commits)}개 커밋 발견")
        return commits

    def get_commit_files(self, sha: str) -> List[Dict]:
        """
        커밋에서 변경된 파일 목록 가져오기

        Args:
            sha: 커밋 SHA

        Returns:
            변경된 파일 리스트 [{'filename': '...', 'status': 'added', ...}]
        """
        url = f"{self.base_url}/repos/{self.username}/{self.baekjoon_repo}/commits/{sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        commit_data = response.json()
        return commit_data.get('files', [])

    def get_file_content(self, file_path: str, ref: str = 'main') -> Optional[str]:
        """
        파일 내용 가져오기

        Args:
            file_path: 레포 내 파일 경로 (예: '백준/Silver/24511. queuestack/README.md')
            ref: 브랜치 또는 커밋 SHA (기본값: main)

        Returns:
            파일 내용 (UTF-8 디코딩)
        """
        url = f"{self.base_url}/repos/{self.username}/{self.baekjoon_repo}/contents/{file_path}"
        params = {'ref': ref}

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 404:
            logger.warning(f"파일을 찾을 수 없음: {file_path}")
            return None

        response.raise_for_status()
        file_data = response.json()

        # GitHub API는 base64로 인코딩된 content 반환
        import base64
        content = base64.b64decode(file_data['content']).decode('utf-8')
        return content

    def filter_baekjoon_files(self, files: List[Dict]) -> List[Dict]:
        """
        백준 관련 파일만 필터링

        Args:
            files: 커밋의 파일 리스트

        Returns:
            백준 폴더의 README.md 파일들
        """
        baekjoon_files = []

        for file in files:
            filename = file['filename']

            # '백준/' 또는 'baekjoon/' 경로이면서 README.md인 파일
            if ('백준/' in filename or 'baekjoon/' in filename.lower()) and \
               filename.endswith('README.md'):
                baekjoon_files.append(file)

        return baekjoon_files

    def extract_problem_info_from_path(self, file_path: str) -> Optional[Dict]:
        """
        파일 경로에서 문제 정보 추출

        Args:
            file_path: 예) '백준/Silver/24511. queuestack/README.md'

        Returns:
            {'tier': 'Silver', 'problem_folder': '24511. queuestack', 'file_path': ...}
        """
        parts = file_path.split('/')

        # 백준/Tier/문제폴더/README.md 구조 확인
        if len(parts) < 4:
            return None

        tier = parts[1]  # Silver, Bronze, Gold 등
        problem_folder = parts[2]  # "24511. queuestack"

        return {
            'tier': tier,
            'problem_folder': problem_folder,
            'file_path': file_path,
            'problem_dir': '/'.join(parts[:-1])  # README.md 제외한 디렉토리
        }

    def find_code_file(self, problem_dir: str, sha: str) -> Optional[str]:
        """
        문제 디렉토리에서 코드 파일 찾기

        Args:
            problem_dir: 문제 디렉토리 경로
            sha: 커밋 SHA

        Returns:
            코드 파일 경로 (예: '백준/Silver/24511. queuestack/queuestack.cc')
        """
        # GitHub API로 디렉토리 목록 가져오기
        url = f"{self.base_url}/repos/{self.username}/{self.baekjoon_repo}/contents/{problem_dir}"
        params = {'ref': sha}

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            return None

        contents = response.json()

        # README.md가 아닌 파일 찾기 (코드 파일)
        for item in contents:
            if item['type'] == 'file' and item['name'] != 'README.md':
                return item['path']

        return None

    def export(self, target_date: datetime = None) -> List[Dict]:
        """
        특정 날짜에 제출된 백준 문제 수집

        Args:
            target_date: 수집 대상 날짜 (기본값: 오늘)

        Returns:
            문제 리스트 [{'readme_path': ..., 'code_path': ..., 'commit_sha': ...}, ...]
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc)
        else:
            # date 객체를 datetime으로 변환
            if isinstance(target_date, date) and not isinstance(target_date, datetime):
                target_date = datetime.combine(target_date, datetime.min.time())

            # naive datetime을 UTC로 변환
            if target_date.tzinfo is None:
                target_date = target_date.replace(tzinfo=timezone.utc)

        # 당일 00:00 ~ 23:59
        today_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        logger.info(f"백준 문제 수집: {today_start.date()}")

        # 1. 당일 커밋 가져오기
        commits = self.get_commits(today_start, today_end)

        if not commits:
            logger.info("당일 커밋이 없습니다.")
            return []

        # 2. 각 커밋에서 백준 파일 찾기
        problems = []

        for commit in commits:
            sha = commit['sha']
            message = commit['commit']['message']

            logger.info(f"커밋 분석: {message[:50]}...")

            # 커밋에서 변경된 파일 가져오기
            files = self.get_commit_files(sha)

            # 백준 README.md 파일만 필터링
            baekjoon_files = self.filter_baekjoon_files(files)

            for file in baekjoon_files:
                file_path = file['filename']
                problem_info = self.extract_problem_info_from_path(file_path)

                if not problem_info:
                    continue

                # 코드 파일 찾기
                code_path = self.find_code_file(problem_info['problem_dir'], sha)

                problems.append({
                    'readme_path': file_path,
                    'code_path': code_path,
                    'commit_sha': sha,
                    'commit_message': message,
                    'commit_date': commit['commit']['committer']['date'],
                    'tier': problem_info['tier'],
                    'problem_folder': problem_info['problem_folder']
                })

                logger.info(f"[OK] 백준 문제 발견: {problem_info['problem_folder']} ({problem_info['tier']})")

        logger.info(f"총 {len(problems)}개 문제 수집 완료")
        return problems


if __name__ == '__main__':
    from datetime import date

    exporter = BaekjoonExporter()

    # 오늘 문제 수집
    problems = exporter.export_today()

    print(f"\n총 {len(problems)}개 문제 수집됨:")
    for p in problems:
        print(f"  - {p['problem_folder']} ({p['tier']})")
        print(f"    README: {p['readme_path']}")
        print(f"    코드: {p['code_path']}")
