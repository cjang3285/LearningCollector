#!/usr/bin/env python3
"""
블로그 포스트 게시

data/draft/post_draft_{날짜}.md → 블로그 API 호출
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date, datetime
from typing import Dict
import requests

from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정
logger = setup_logging(get_log_file('publish'), __name__)

# 데이터 디렉토리
DRAFT_DIR = PROJECT_ROOT / 'data' / 'draft'

# 블로그 API 설정
BLOG_API_URL = os.getenv('BLOG_API_URL', 'http://localhost:3000/api/posts')
BLOG_API_TOKEN = os.getenv('BLOG_API_TOKEN', '')
MOCK_MODE = os.getenv('BLOG_MOCK_MODE', 'true').lower() == 'true'


def load_draft(target_date: date) -> str:
    """초안 파일 읽기"""
    file_path = DRAFT_DIR / f'post_draft_{target_date}.md'

    if not file_path.exists():
        raise FileNotFoundError(f"초안 파일이 없습니다: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_title(content: str) -> str:
    """마크다운에서 제목 추출"""
    lines = content.split('\n')
    for line in lines:
        if line.startswith('#'):
            return line.replace('#', '').strip()
    return f"Learning Log"


def publish_via_api(target_date: date, status: str = 'draft') -> Dict:
    """
    블로그 API로 포스트 게시

    Args:
        target_date: 날짜
        status: 'draft' (초안) 또는 'published' (게시)

    Returns:
        API 응답 (post_id, status 등)
    """
    # 초안 읽기
    content = load_draft(target_date)
    title = extract_title(content)

    # Mock 모드
    if MOCK_MODE:
        logger.info("🧪 Mock 모드: API 호출 시뮬레이션")
        mock_response = {
            'id': 12345,
            'title': title,
            'status': status,
            'created_date': str(target_date),
            'created_at': datetime.now().isoformat(),
            'message': 'Mock: 게시 성공'
        }
        logger.info(f"Mock 응답: {json.dumps(mock_response, ensure_ascii=False, indent=2)}")
        return mock_response

    # 실제 API 호출
    logger.info(f"📡 블로그 API 호출: {BLOG_API_URL}")

    payload = {
        'title': title,
        'content': content,
        'status': status,
        'created_date': str(target_date)
    }

    headers = {
        'Content-Type': 'application/json'
    }

    if BLOG_API_TOKEN:
        headers['Authorization'] = f'Bearer {BLOG_API_TOKEN}'

    try:
        response = requests.post(
            BLOG_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        result = response.json()

        logger.info(f"✅ 게시 성공: Post ID={result.get('id')}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API 호출 실패: {e}")
        raise


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='블로그에 초안 게시',
        epilog='''
사용 예시:
  # Mock 모드로 테스트
  python publish_to_blog.py

  # 특정 날짜 초안 게시 (Mock)
  python publish_to_blog.py --date 2026-01-15

  # 바로 게시 (published 상태)
  python publish_to_blog.py --publish

  # 실제 API 호출 (BLOG_MOCK_MODE=false)
  BLOG_MOCK_MODE=false python publish_to_blog.py --publish
        '''
    )
    parser.add_argument('--date', type=str, help='날짜 (YYYY-MM-DD)')
    parser.add_argument('--publish', action='store_true', help='바로 게시 (기본: 초안)')

    args = parser.parse_args()

    # 날짜 파싱
    target_date = date.today()
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    status = 'published' if args.publish else 'draft'

    try:
        logger.info("="*60)
        logger.info(f"블로그 포스트 게시 시작 - {target_date}")
        logger.info("="*60)

        if MOCK_MODE:
            logger.warning("⚠️  Mock 모드 활성화 (실제 API 호출 안 함)")
            logger.warning("실제 게시하려면: BLOG_MOCK_MODE=false 설정")

        # API 호출
        result = publish_via_api(target_date, status)

        logger.info("\n" + "="*60)
        logger.info("게시 완료")
        logger.info("="*60)
        logger.info(f"Post ID: {result.get('id')}")
        logger.info(f"상태: {result.get('status')}")
        logger.info(f"제목: {result.get('title')}")
        logger.info("="*60)

        sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"초안 파일을 찾을 수 없습니다: {e}")
        logger.info("먼저 generate_post_draft.py를 실행하세요")
        sys.exit(1)

    except Exception as e:
        logger.error(f"게시 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
