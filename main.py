#!/usr/bin/env python3
"""
Learning Artifacts ETL Pipeline - Main Entry Point

모든 학습 활동을 수집하여 DB에 저장하는 메인 프로그램
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date, datetime
from typing import Dict
import logging

from collectors.github_collector import GitHubCollector
from collectors.claude_collector import ClaudeCollector
from collectors.baekjoon_collector import BaekjoonCollector
from config.settings import get_log_file, COLLECT_GITHUB, COLLECT_CLAUDE, COLLECT_BAEKJOON

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('main')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LearningETL:
    """학습 아티팩트 ETL 메인 클래스"""

    def __init__(self):
        self.github_collector = GitHubCollector() if COLLECT_GITHUB else None
        self.claude_collector = ClaudeCollector() if COLLECT_CLAUDE else None
        self.baekjoon_collector = BaekjoonCollector() if COLLECT_BAEKJOON else None

    def run(self, target_date: date = None, claude_zip_path: str = None, all_dates: bool = False) -> Dict:
        """
        전체 ETL 프로세스 실행

        Args:
            target_date: 수집 대상 날짜 (기본값: 오늘)
            claude_zip_path: Claude 수동 다운로드 ZIP 파일 경로

        Returns:
            {
                'date': date,
                'github': {...},
                'claude': {...},
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
            'baekjoon': None,
            'summary': {}
        }

        # 1. GitHub 수집
        if self.github_collector:
            logger.info("\n[GitHub] 데이터 수집 시작...")
            results['github'] = self.github_collector.collect(target_date)
        else:
            logger.info("\n[GitHub] 수집 비활성화됨")

        # 2. Claude 수집 (수동 다운로드 방식)
        if self.claude_collector and claude_zip_path:
            logger.info("\n[Claude] 데이터 수집 시작...")
            results['claude'] = self.claude_collector.collect(claude_zip_path, target_date, all_dates=all_dates)
        elif self.claude_collector:
            logger.info("\n[Claude] ZIP 파일이 제공되지 않아 건너뜀")
        else:
            logger.info("\n[Claude] 수집 비활성화됨")

        # 3. 백준 수집
        if self.baekjoon_collector:
            logger.info("\n[Baekjoon] 데이터 수집 시작...")
            results['baekjoon'] = self.baekjoon_collector.collect(target_date)
        else:
            logger.info("\n[Baekjoon] 수집 비활성화됨")

        # 4. 요약
        total_artifacts = 0
        if results['github']:
            total_artifacts += results['github'].get('commits_count', 0)
        if results['claude']:
            total_artifacts += results['claude'].get('conversations_count', 0)
        if results['baekjoon']:
            total_artifacts += results['baekjoon'].get('solutions_count', 0)

        results['summary'] = {
            'total_artifacts': total_artifacts,
            'github_commits': results['github'].get('commits_count', 0) if results['github'] else 0,
            'claude_conversations': results['claude'].get('conversations_count', 0) if results['claude'] else 0,
            'baekjoon_solutions': results['baekjoon'].get('solutions_count', 0) if results['baekjoon'] else 0,
            'success': all([
            results.get('github', {}).get('success', True) if results.get('github') else True,
            results.get('claude', {}).get('success', True) if results.get('claude') else True,
            results.get('baekjoon', {}).get('success', True) if results.get('baekjoon') else True
        ])
        }

        # 5. 결과 출력
        logger.info("\n" + "="*60)
        logger.info("수집 완료")
        logger.info("="*60)
        logger.info(f"총 아티팩트: {results['summary']['total_artifacts']}개")
        logger.info(f"  - GitHub: {results['summary']['github_commits']}개")
        logger.info(f"  - Claude: {results['summary']['claude_conversations']}개")
        logger.info(f"  - 백준: {results['summary']['baekjoon_solutions']}개")
        logger.info("="*60)

        return results


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Learning Artifacts ETL Pipeline')
    parser.add_argument('--claude-zip', type=str, help='Claude 수동 다운로드 ZIP 파일 경로')
    parser.add_argument('--date', type=str, help='수집 대상 날짜 (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='날짜 제한 없이 모든 대화 수집')
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    etl = LearningETL()
    results = etl.run(target_date=target_date, claude_zip_path=args.claude_zip, all_dates=getattr(args, "all", False))

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
