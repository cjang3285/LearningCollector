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
from interfaces import CollectionContext
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
        import_zip: bool = False,
        ai_chat_files: list = None,
        ai_chat_scan: bool = False,
        ai_chat_download_dir: str = None,
        all_dates: bool = False,
        skip_github: bool = False,
        skip_baekjoon: bool = False,
        skip_ai_chat: bool = False
    ) -> Dict:
        """
        전체 ETL 프로세스 실행

        Args:
            target_date: 수집 대상 날짜 (기본값: 오늘)
            import_zip: Claude ZIP 파일 자동 감지 여부 (첫 마이그레이션용)
            ai_chat_files: AI 채팅 마크다운 파일 리스트
            ai_chat_scan: 다운로드 폴더 스캔 여부 (기본: True)
            ai_chat_download_dir: 다운로드 폴더 경로
            all_dates: ZIP 임포트 시 모든 날짜 대화 수집 여부
            skip_github: GitHub 수집 제외
            skip_baekjoon: 백준 수집 제외
            skip_ai_chat: AI Chat 수집 제외

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
        if skip_github:
            logger.info("\n[GitHub] 수집 제외됨 (--skip-github)")
        else:
            github_collector = self.collectors.get('github')
            if github_collector:
                logger.info("\n[GitHub] 데이터 수집 시작...")
                context = CollectionContext(target_date=target_date, options={})
                result = github_collector.collect(context)
                # CollectionResult를 dict 형식으로 변환 (하위 호환성)
                results['github'] = {
                    'success': result.success,
                    'date': result.date,
                    'commits_count': result.items_count,
                    'artifact_ids': result.artifact_ids,
                    **result.metadata
                }
            else:
                logger.info("\n[GitHub] 수집 비활성화됨")

        # 2. Claude Migration (첫 이용 시 ZIP 마이그레이션)
        if import_zip:
            from bulk_import.claude_collector import ClaudeMigrationCollector
            logger.info("\n[Claude Migration] ZIP 파일 자동 감지 및 마이그레이션 중...")
            claude_collector = ClaudeMigrationCollector()
            results['claude'] = claude_collector.collect(
                zip_path=None,  # 자동 감지
                target_date=target_date,
                all_dates=all_dates
            )
        else:
            logger.debug("\n[Claude Migration] ZIP 임포트 비활성화됨 (일상 사용은 --ai-chat-scan 사용)")

        # 3. AI Chat 수집 (Claude, ChatGPT, Gemini 마크다운)
        if skip_ai_chat:
            logger.info("\n[AI Chat] 수집 제외됨 (--skip-ai-chat)")
        else:
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
        if skip_baekjoon:
            logger.info("\n[Baekjoon] 수집 제외됨 (--skip-baekjoon)")
        else:
            baekjoon_collector = self.collectors.get('baekjoon')
            if baekjoon_collector:
                logger.info("\n[Baekjoon] 데이터 수집 시작...")
                context = CollectionContext(target_date=target_date, options={})
                result = baekjoon_collector.collect(context)
                # CollectionResult를 dict 형식으로 변환 (하위 호환성)
                results['baekjoon'] = {
                    'success': result.success,
                    'date': result.date,
                    'solutions_count': result.items_count,
                    'artifact_ids': result.artifact_ids,
                    **result.metadata
                }
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

    parser = argparse.ArgumentParser(
        description='Learning Artifacts ETL Pipeline',
        epilog='''
사용 예시:
  # 기본 실행 (GitHub + Baekjoon + AI Chat 자동 스캔)
  python main.py

  # GitHub만 제외하고 실행
  python main.py --skip-github

  # AI Chat만 수집
  python main.py --skip-github --skip-baekjoon

  # Claude ZIP 파일 임포트 (첫 마이그레이션용)
  python main.py --import-zip --all
        '''
    )
    parser.add_argument(
        '--import-zip',
        action='store_true',
        help='[첫 마이그레이션용] Claude ZIP 파일 자동 감지 및 임포트'
    )
    parser.add_argument(
        '--ai-chat',
        nargs='*',
        help='AI 채팅 마크다운 파일 직접 지정 (Claude, ChatGPT, Gemini)'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        help='다운로드 폴더 경로 (기본값: AI_CHAT_DOWNLOAD_DIR 환경변수 또는 ~/Downloads)'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='수집 대상 날짜 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='[--import-zip 전용] ZIP의 모든 대화 수집 (날짜 무관)'
    )
    parser.add_argument(
        '--skip-github',
        action='store_true',
        help='GitHub 수집 제외'
    )
    parser.add_argument(
        '--skip-baekjoon',
        action='store_true',
        help='백준 수집 제외'
    )
    parser.add_argument(
        '--skip-ai-chat',
        action='store_true',
        help='AI Chat 수집 제외'
    )
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    # AI Chat 기본 실행: --ai-chat 파일 지정 없고, --skip-ai-chat 없으면 자동 스캔
    ai_chat_scan = not args.skip_ai_chat and not args.ai_chat

    etl = LearningETL()
    results = etl.run(
        target_date=target_date,
        import_zip=args.import_zip,
        ai_chat_files=args.ai_chat,
        ai_chat_scan=ai_chat_scan,
        ai_chat_download_dir=args.download_dir or AI_CHAT_DOWNLOAD_DIR,
        all_dates=args.all,
        skip_github=args.skip_github,
        skip_baekjoon=args.skip_baekjoon,
        skip_ai_chat=args.skip_ai_chat
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
