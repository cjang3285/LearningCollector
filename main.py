#!/usr/bin/env python3
"""
Learning Artifacts ETL Pipeline - Main Entry Point

모든 학습 활동을 수집하여 DB에 저장하는 메인 프로그램
CollectorFactory 적용 (SOLID - OCP)
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date, datetime
from typing import Dict
import logging

from factories import CollectorFactory
from config.settings import get_log_file, AI_CHAT_DOWNLOAD_DIR
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('main'), __name__)


class LearningETL:
    """
    학습 아티팩트 ETL 메인 클래스 (OCP 적용)

    CollectorFactory를 사용하여 설정 기반으로 Collector 생성
    새로운 Collector 추가 시 이 클래스 수정 불필요!
    """

    def __init__(self):
        # CollectorFactory로 모든 Collector 생성 (OCP 적용)
        self.collectors = CollectorFactory.create_all_collectors(enabled_only=True)

        logger.info(f"활성화된 Collector: {list(self.collectors.keys())}")

    def run(
        self,
        target_date: date = None,
        claude_zip_path: str = None,
        ai_chat_files: list = None,
        ai_chat_scan: bool = False,
        ai_chat_download_dir: str = None,
        all_dates: bool = False
    ) -> Dict:
        """
        전체 ETL 프로세스 실행

        Args:
            target_date: 수집 대상 날짜 (기본값: 오늘)
            claude_zip_path: Claude 수동 다운로드 ZIP 파일 경로
            ai_chat_files: AI 채팅 마크다운 파일 리스트
            ai_chat_scan: 다운로드 폴더 스캔 여부

        Returns:
            {
                'date': date,
                'github': {...},
                'claude': {...},
                'ai_chat': {...},
                'baekjoon': {...},
                'summary': {...}
            }
        """
        target_date = target_date or date.today()

        logger.info("="*60)
        logger.info(f"Learning Artifacts ETL - {target_date}")
        logger.info("="*60)

        results = {
            'date': str(target_date),
            'timestamp': datetime.now().isoformat(),
            'github': None,
            'claude': None,
            'ai_chat': None,
            'baekjoon': None,
            'summary': {}
        }

        # 1. GitHub 수집
        github_collector = self.collectors.get('github')
        if github_collector:
            logger.info("\n[GitHub] 데이터 수집 시작...")
            results['github'] = github_collector.collect_github(target_date)
        else:
            logger.info("\n[GitHub] 수집 비활성화됨")

        # 2. Claude Migration (첫 이용 시 ZIP 마이그레이션)
        if claude_zip_path:
            claude_migration_collector = CollectorFactory.create_collector('claude_migration')
            if claude_migration_collector:
                logger.info("\n[Claude Migration] ZIP 파일에서 대화 마이그레이션 중...")
                results['claude'] = claude_migration_collector.collect(claude_zip_path, target_date, all_dates=all_dates)
        else:
            logger.info("\n[Claude Migration] ZIP 파일 미제공 (일상 사용은 --ai-chat-scan 사용)")

        # 3. AI Chat 수집 (Claude, ChatGPT, Gemini 마크다운)
        ai_chat_collector = self.collectors.get('ai_chat')
        if ai_chat_collector:
            if ai_chat_files:
                logger.info("\n[AI Chat] 마크다운 파일 수집 시작...")
                results['ai_chat'] = ai_chat_collector.collect_from_files(ai_chat_files, target_date)
            elif ai_chat_scan:
                logger.info("\n[AI Chat] 다운로드 폴더 스캔 중...")
                if ai_chat_download_dir:
                    logger.info(f"다운로드 폴더: {ai_chat_download_dir}")
                results['ai_chat'] = ai_chat_collector.collect_from_downloads(
                    download_dir=ai_chat_download_dir,
                    target_date=target_date
                )
            else:
                logger.info("\n[AI Chat] 파일이 제공되지 않아 건너뜀")
        else:
            logger.info("\n[AI Chat] 수집 비활성화됨")

        # 4. 백준 수집
        baekjoon_collector = self.collectors.get('baekjoon')
        if baekjoon_collector:
            logger.info("\n[Baekjoon] 데이터 수집 시작...")
            results['baekjoon'] = baekjoon_collector.collect_baekjoon(target_date)
        else:
            logger.info("\n[Baekjoon] 수집 비활성화됨")

        # 5. 요약
        total_artifacts = 0
        if results['github']:
            total_artifacts += results['github'].get('commits_count', 0)
        if results['claude']:
            total_artifacts += results['claude'].get('conversations_count', 0)
        if results['ai_chat']:
            total_artifacts += results['ai_chat'].get('conversations_count', 0)
        if results['baekjoon']:
            total_artifacts += results['baekjoon'].get('solutions_count', 0)

        results['summary'] = {
            'total_artifacts': total_artifacts,
            'github_commits': results['github'].get('commits_count', 0) if results['github'] else 0,
            'claude_conversations': results['claude'].get('conversations_count', 0) if results['claude'] else 0,
            'ai_chat_conversations': results['ai_chat'].get('conversations_count', 0) if results['ai_chat'] else 0,
            'baekjoon_solutions': results['baekjoon'].get('solutions_count', 0) if results['baekjoon'] else 0,
            'success': all([
                results.get('github', {}).get('success', True) if results.get('github') else True,
                results.get('claude', {}).get('success', True) if results.get('claude') else True,
                results.get('ai_chat', {}).get('success', True) if results.get('ai_chat') else True,
                results.get('baekjoon', {}).get('success', True) if results.get('baekjoon') else True
            ])
        }

        # 6. 결과 출력
        logger.info("\n" + "="*60)
        logger.info("수집 완료")
        logger.info("="*60)
        logger.info(f"총 아티팩트: {results['summary']['total_artifacts']}개")
        logger.info(f"  - GitHub: {results['summary']['github_commits']}개")
        logger.info(f"  - Claude: {results['summary']['claude_conversations']}개")
        logger.info(f"  - AI Chat: {results['summary']['ai_chat_conversations']}개")
        logger.info(f"  - 백준: {results['summary']['baekjoon_solutions']}개")
        logger.info("="*60)

        return results


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Learning Artifacts ETL Pipeline')
    parser.add_argument('--claude-zip', type=str, help='[첫 마이그레이션용] Claude ZIP 파일 경로')
    parser.add_argument('--ai-chat', nargs='*', help='AI 채팅 마크다운 파일 (Claude, ChatGPT, Gemini)')
    parser.add_argument('--ai-chat-scan', action='store_true', help='[일상 사용] 다운로드 폴더 AI 채팅 자동 스캔')
    parser.add_argument('--download-dir', type=str, help='다운로드 폴더 경로 (기본값: ~/Downloads)')
    parser.add_argument('--date', type=str, help='수집 대상 날짜 (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='[Claude ZIP 전용] 전체 대화 수집')
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    etl = LearningETL()
    results = etl.run(
        target_date=target_date,
        claude_zip_path=args.claude_zip,
        ai_chat_files=args.ai_chat,
        ai_chat_scan=args.ai_chat_scan,
        ai_chat_download_dir=args.download_dir or AI_CHAT_DOWNLOAD_DIR,
        all_dates=getattr(args, "all", False)
    )

    # 결과를 JSON 파일로도 저장
    import json
    output_file = PROJECT_ROOT / 'logs' / f'etl_result_{date.today()}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"\n결과 저장: {output_file}")

    # 종료 코드
    sys.exit(0 if results['summary']['success'] else 1)


if __name__ == '__main__':
    main()
