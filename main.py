#!/usr/bin/env python3
"""
학습 데이터 수집 도구 (간소화 버전)

GitHub 커밋, AI Chat, Baekjoon 풀이를 수집하여 JSON 파일로 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date, datetime, timedelta
from typing import Dict, List
import logging

from config.settings import get_log_file, AI_CHAT_DOWNLOAD_DIR
from config.logging_config import setup_logging
from utils.collection_tracker import get_collection_date_range

# Loaders
from load.github_load import GitHubLoader
from load.ai_chat_load import AILoadWatcher
from load.baekjoon_load import BaekjoonLoader

# Parsers
from parse.github_parse import GitHubParser
from parse.ai_chat_parse import AIMarkdownParser
from parse.baekjoon_parse import BaekjoonParser

# 로깅 설정
logger = setup_logging(get_log_file('main'), __name__)

# 데이터 디렉토리
DATA_DIR = PROJECT_ROOT / 'data'
COLLECTION_LOG_DIR = DATA_DIR / 'collection_log'
DRAFT_DIR = DATA_DIR / 'draft'

# 디렉토리 생성
DATA_DIR.mkdir(exist_ok=True)
COLLECTION_LOG_DIR.mkdir(exist_ok=True)
DRAFT_DIR.mkdir(exist_ok=True)


def collect_github(target_date: date) -> Dict:
    """GitHub 커밋 수집"""
    logger.info(f"\n[GitHub] {target_date} 데이터 수집 중...")

    try:
        # Load
        loader = GitHubLoader()
        commits = loader.load(target_date)

        if not commits:
            logger.info("[GitHub] 수집된 커밋 없음")
            return {'commits': [], 'summary': {}}

        # Parse
        parser = GitHubParser()
        parsed_commits = parser.parse_commits(commits)
        summary = parser.get_summary(parsed_commits)

        logger.info(f"[GitHub] {len(parsed_commits)}개 커밋 수집 완료")
        return {
            'commits': parsed_commits,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"[GitHub] 수집 실패: {e}", exc_info=True)
        return {'commits': [], 'summary': {}, 'error': str(e)}


def collect_ai_chat(target_date: date, download_dir: str = None) -> Dict:
    """AI Chat 대화 수집"""
    logger.info(f"\n[AI Chat] {target_date} 데이터 수집 중...")

    try:
        # Load - 다운로드 폴더 스캔
        watcher = AILoadWatcher(download_dir or AI_CHAT_DOWNLOAD_DIR)
        files = watcher.scan_existing()

        # 오늘 날짜 파일만 필터링 (파일 수정 시간 기준)
        today_files = []
        for file_path in files:
            file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime).date()
            if file_mtime == target_date:
                today_files.append(file_path)

        if not today_files:
            logger.info("[AI Chat] 오늘 수집된 파일 없음")
            return {'conversations': []}

        # Parse
        parser = AIMarkdownParser()
        conversations = parser.parse_multiple(today_files)

        logger.info(f"[AI Chat] {len(conversations)}개 대화 수집 완료")
        return {
            'conversations': conversations
        }

    except Exception as e:
        logger.error(f"[AI Chat] 수집 실패: {e}", exc_info=True)
        return {'conversations': [], 'error': str(e)}


def collect_baekjoon(target_date: date) -> Dict:
    """Baekjoon 풀이 수집"""
    logger.info(f"\n[Baekjoon] {target_date} 데이터 수집 중...")

    try:
        # Load
        loader = BaekjoonLoader()
        problems = loader.load(target_date)

        if not problems:
            logger.info("[Baekjoon] 수집된 풀이 없음")
            return {'solutions': []}

        # Parse
        parser = BaekjoonParser()
        parsed_problems = parser.parse_problems(problems, loader)

        logger.info(f"[Baekjoon] {len(parsed_problems)}개 풀이 수집 완료")
        return {
            'solutions': parsed_problems
        }

    except Exception as e:
        logger.error(f"[Baekjoon] 수집 실패: {e}", exc_info=True)
        return {'solutions': [], 'error': str(e)}


def save_daily_data(target_date: date, data: Dict) -> Path:
    """날짜별 데이터를 JSON 파일로 저장"""
    file_path = COLLECTION_LOG_DIR / f'collect_result_{target_date}.json'

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"\n데이터 저장 완료: {file_path}")
    return file_path


def collect_all(
    target_date: date = None,
    skip_github: bool = False,
    skip_ai_chat: bool = False,
    skip_baekjoon: bool = False
) -> Dict:
    """전체 수집 실행"""
    target_date = target_date or date.today()

    logger.info("="*60)
    logger.info(f"학습 데이터 수집 시작 - {target_date}")
    logger.info("="*60)

    results = {
        'date': str(target_date),
        'timestamp': datetime.now().isoformat(),
        'github': None if skip_github else collect_github(target_date),
        'ai_chat': None if skip_ai_chat else collect_ai_chat(target_date),
        'baekjoon': None if skip_baekjoon else collect_baekjoon(target_date)
    }

    # Summary
    summary = {
        'total_commits': len(results['github']['commits']) if results.get('github') else 0,
        'total_conversations': len(results['ai_chat']['conversations']) if results.get('ai_chat') else 0,
        'total_solutions': len(results['baekjoon']['solutions']) if results.get('baekjoon') else 0
    }
    results['summary'] = summary

    logger.info("\n" + "="*60)
    logger.info("수집 완료")
    logger.info("="*60)
    logger.info(f"GitHub 커밋: {summary['total_commits']}개")
    logger.info(f"AI Chat: {summary['total_conversations']}개")
    logger.info(f"Baekjoon: {summary['total_solutions']}개")
    logger.info("="*60)

    # 파일 저장
    save_daily_data(target_date, results)

    return results


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='학습 데이터 수집 도구',
        epilog='''
사용 예시:
  # 오늘 데이터 수집
  python main.py

  # 특정 날짜 수집
  python main.py --date 2026-01-15

  # GitHub만 제외
  python main.py --skip-github
        '''
    )
    parser.add_argument('--date', type=str, help='수집 날짜 (YYYY-MM-DD)')
    parser.add_argument('--skip-github', action='store_true', help='GitHub 수집 제외')
    parser.add_argument('--skip-ai-chat', action='store_true', help='AI Chat 수집 제외')
    parser.add_argument('--skip-baekjoon', action='store_true', help='Baekjoon 수집 제외')

    args = parser.parse_args()

    # 날짜 파싱
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    # 수집 실행
    try:
        results = collect_all(
            target_date=target_date,
            skip_github=args.skip_github,
            skip_ai_chat=args.skip_ai_chat,
            skip_baekjoon=args.skip_baekjoon
        )

        # 성공 여부 체크
        success = not any(
            results[key] and results[key].get('error')
            for key in ['github', 'ai_chat', 'baekjoon']
            if results.get(key)
        )

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"수집 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
