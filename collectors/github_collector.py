#!/usr/bin/env python3
"""
GitHub Collector - GitHub 데이터 수집 + 파싱 + DB 저장
ICollector 인터페이스 구현 (SOLID - DIP, SRP)
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
from interfaces import ICollector, CollectionContext, CollectionResult, CollectionError
from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('github_collector'), __name__)


class GitHubCollector(ICollector):
    """GitHub 데이터 수집 통합 (ICollector 구현)"""

    def __init__(self):
        self.exporter = GitHubExporter()
        self.parser = GitHubParser()
        self.saver = GitHubSaver()

    # ============================================
    # ICollector 인터페이스 구현
    # ============================================

    def collect(self, context: CollectionContext) -> CollectionResult:
        """
        GitHub 데이터 수집 실행 (ICollector 인터페이스)

        Args:
            context: 수집 컨텍스트
                - target_date: 수집 대상 날짜
                - options: {} (GitHub는 옵션 불필요)

        Returns:
            수집 결과 (CollectionResult)
        """
        try:
            result_dict = self.collect_github(context.target_date)

            return CollectionResult(
                success=result_dict['success'],
                date=context.target_date,
                items_count=result_dict['commits_count'],
                artifact_ids=result_dict['artifact_ids'],
                metadata={'source': 'github'},
                error=result_dict.get('error')
            )

        except Exception as e:
            logger.error(f"GitHub 수집 실패: {e}")
            return CollectionResult(
                success=False,
                date=context.target_date,
                items_count=0,
                artifact_ids=[],
                metadata={'source': 'github'},
                error=str(e)
            )

    def should_run(self, context: CollectionContext) -> bool:
        """
        수집 실행 여부 판단 (ICollector 인터페이스)

        Args:
            context: 수집 컨텍스트

        Returns:
            항상 True (GitHub는 매일 수집)
        """
        return True

    def get_name(self) -> str:
        """
        Collector 이름 반환 (ICollector 인터페이스)

        Returns:
            "github"
        """
        return "github"

    # ============================================
    # 편의 메서드 (기존 호환성 유지)
    # ============================================

    def collect_github(self, target_date: date = None) -> Dict:
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
