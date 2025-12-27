#!/usr/bin/env python3
"""
Configuration Settings

환경변수 및 프로젝트 설정을 관리합니다.
"""

import os
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# GitHub 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # 환경변수에서만 가져오기
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'cjang3285')

# 백준 설정
BAEKJOON_HANDLE = os.getenv('BAEKJOON_HANDLE', 'andy1692')

# 디렉토리 설정
TEMP_DIR = PROJECT_ROOT / 'temp'
LOGS_DIR = PROJECT_ROOT / 'logs'
ARTIFACTS_DIR = PROJECT_ROOT / 'learning_artifacts'

# 디렉토리 생성
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Claude 설정 (수동 다운로드 방식)
CLAUDE_DOWNLOAD_DIR = TEMP_DIR / 'claude_downloads'
CLAUDE_DOWNLOAD_DIR.mkdir(exist_ok=True)

# 백준 설정
BAEKJOON_COOKIES_PATH = TEMP_DIR / 'baekjoon_cookies.json'
BAEKJOON_CACHE_PATH = TEMP_DIR / 'baekjoon_solved.json'

# 로깅 설정
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# API 설정
GITHUB_API_BASE = 'https://api.github.com'
SOLVED_AC_API_BASE = 'https://solved.ac/api/v3'
BAEKJOON_BASE_URL = 'https://www.acmicpc.net'

# Selenium 설정
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 30

# 데이터 수집 설정
COLLECT_CLAUDE = True
COLLECT_GITHUB = True
COLLECT_BAEKJOON = True

# PostgreSQL 설정 (블로그 DB)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'my_blog')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def get_db_config():
    """DB 연결 설정 반환"""
    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD
    }

def validate_config():
    """필수 설정값 검증"""
    errors = []

    if COLLECT_GITHUB and not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN이 설정되지 않았습니다.")

    if COLLECT_GITHUB and not GITHUB_USERNAME:
        errors.append("GITHUB_USERNAME이 설정되지 않았습니다.")

    if COLLECT_BAEKJOON and not BAEKJOON_HANDLE:
        errors.append("BAEKJOON_HANDLE이 설정되지 않았습니다.")

    if errors:
        raise ValueError("설정 오류:\n" + "\n".join(errors))

    return True

def get_log_file(module_name):
    """모듈별 로그 파일 경로 반환"""
    return LOGS_DIR / f'{module_name}.log'

if __name__ == '__main__':
    print("=== Configuration Settings ===")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"GITHUB_USERNAME: {GITHUB_USERNAME}")
    print(f"GITHUB_TOKEN: {'*' * 20}...{GITHUB_TOKEN[-4:]}")
    print(f"BAEKJOON_HANDLE: {BAEKJOON_HANDLE}")
    print(f"TEMP_DIR: {TEMP_DIR}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    print(f"ARTIFACTS_DIR: {ARTIFACTS_DIR}")

    try:
        validate_config()
        print("\n[OK] 설정 검증 완료")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
