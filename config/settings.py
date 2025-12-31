#!/usr/bin/env python3
"""
Configuration Settings

환경변수 및 프로젝트 설정을 관리합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# .env 파일 로드
load_dotenv(PROJECT_ROOT / '.env', override=True)

# ============================================
# GitHub 설정
# ============================================
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # 환경변수에서만 가져오기
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')

# ============================================
# 백준허브 연동 레포 설정
# ============================================
BAEKJOON_HANDLE = os.getenv('BAEKJOON_HANDLE')
BAEKJOON_REPO = os.getenv('BAEKJOON_REPO')  # 백준허브와 연동된 레포지터리

# ============================================
# 디렉토리 설정
# ============================================
TEMP_DIR = PROJECT_ROOT / 'temp'
LOGS_DIR = PROJECT_ROOT / 'logs'
ARTIFACTS_DIR = PROJECT_ROOT / 'learning_artifacts'

# 디렉토리 생성
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Claude Migration (첫 마이그레이션용 ZIP 다운로드)
CLAUDE_MIGRATION_DIR = TEMP_DIR 
CLAUDE_MIGRATION_DIR.mkdir(exist_ok=True)

# AI Chat (마크다운 자동 수집)
AI_CHAT_DOWNLOAD_DIR = os.getenv('AI_CHAT_DOWNLOAD_DIR')

# ============================================
# 로깅 설정
# ============================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============================================
# API 설정
# ============================================
GITHUB_API_BASE = 'https://api.github.com'

# ============================================
# 데이터 수집 설정
# ============================================
COLLECT_GITHUB = os.getenv('COLLECT_GITHUB', 'true').lower() == 'true'
COLLECT_BAEKJOON = os.getenv('COLLECT_BAEKJOON', 'true').lower() == 'true'
COLLECT_AI_CHAT = os.getenv('COLLECT_AI_CHAT', 'true').lower() == 'true'

# Claude 마이그레이션 (첫 이용 시에만 사용, 이후 AI_CHAT 사용)
ENABLE_CLAUDE_MIGRATION = os.getenv('ENABLE_CLAUDE_MIGRATION', 'false').lower() == 'true'

# ============================================
# PostgreSQL 설정 (블로그 DB)
# ============================================
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
    print(f"\n[GitHub]")
    print(f"  USERNAME: {GITHUB_USERNAME}")
    print(f"  TOKEN: {'*' * 20 if GITHUB_TOKEN else 'NOT SET'}")
    print(f"\n[백준]")
    print(f"  HANDLE: {BAEKJOON_HANDLE}")
    print(f"  REPO: {BAEKJOON_REPO}")
    print(f"\n[디렉토리]")
    print(f"  TEMP: {TEMP_DIR}")
    print(f"  LOGS: {LOGS_DIR}")
    print(f"  ARTIFACTS: {ARTIFACTS_DIR}")
    print(f"  CLAUDE_MIGRATION: {CLAUDE_MIGRATION_DIR}")
    print(f"  AI_CHAT_DOWNLOAD: {AI_CHAT_DOWNLOAD_DIR}")
    print(f"\n[데이터 수집]")
    print(f"  GITHUB: {COLLECT_GITHUB}")
    print(f"  BAEKJOON: {COLLECT_BAEKJOON}")
    print(f"  AI_CHAT: {COLLECT_AI_CHAT}")
    print(f"  CLAUDE_MIGRATION: {ENABLE_CLAUDE_MIGRATION}")

    try:
        validate_config()
        print("\n[OK] 설정 검증 완료")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
