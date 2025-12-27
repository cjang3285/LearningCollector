#!/usr/bin/env python3
"""
GitHub Collector - GitHub 데이터 수집 + 파싱 + DB 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from typing import List, Dict
import logging

from export.github_export import GitHubExporter
from parse.github_parse import GitHubParser
from storage.github_saver import GitHubSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('github_collector')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GitHubCollector:
    """GitHub 데이터 수집 통합"""

    def __init__(self):
        self.exporter = GitHubExporter()
        self.parser = GitHubParser()
        self.saver = GitHubSaver()

    def collect(self, target_date: date = None) -> Dict:
        """
        GitHub 데이터 수집 + 파싱 + 저장

        Returns:
            {
                'success': bool,
                'date': date,
                'commits_count': int,
                'artifact_ids': List[int]
            }
        """
        target_date = target_date or date.today()
        logger.info(f"GitHub 데이터 수집 시작: {target_date}")

        try:
            # 1. Export - GitHub API로 커밋 수집
            logger.info("[1/3] GitHub API에서 커밋 수집...")
            commits = self.exporter.export_today()

            if not commits:
                logger.info("수집된 커밋이 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'commits_count': 0,
                    'artifact_ids': []
                }

            # 2. Parse - 데이터 파싱
            logger.info(f"[2/3] {len(commits)}개 커밋 파싱...")
            parsed_commits = self.parser.parse_commits(commits)

            # 3. Save - DB 저장
            logger.info("[3/3] DB에 저장...")
            artifact_ids = self.saver.save_all(commits, target_date)

            logger.info(f"GitHub 수집 완료: {len(artifact_ids)}개 저장")

            return {
                'success': True,
                'date': target_date,
                'commits_count': len(commits),
                'artifact_ids': artifact_ids
            }

        except Exception as e:
            logger.error(f"GitHub 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'commits_count': 0,
                'artifact_ids': [],
                'error': str(e)
            }


if __name__ == '__main__':
    collector = GitHubCollector()
    result = collector.collect()
    print(f"\n결과: {result}")
