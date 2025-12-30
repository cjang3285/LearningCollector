#!/usr/bin/env python3
"""
백준 Collector - 백준 데이터 수집 + 파싱 + DB 저장
백준허브와 연동된 레포지터리에서 자동 푸시된 백준 풀이를 수집합니다.
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

from export.baekjoon_export import BaekjoonExporter
from parse.baekjoon_parse import BaekjoonParser
from storage.baekjoon_saver import BaekjoonSaver
from interfaces import ICollector, CollectionContext, CollectionResult, CollectionError
from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('baekjoon_collector'), __name__)


class BaekjoonCollector(ICollector):
    """백준 데이터 수집 통합 (ICollector 구현)"""

    def __init__(self):
        self.exporter = BaekjoonExporter()
        self.parser = BaekjoonParser()
        self.saver = BaekjoonSaver()

    # ============================================
    # ICollector 인터페이스 구현
    # ============================================

    def collect(self, context: CollectionContext) -> CollectionResult:
        """
        백준 데이터 수집 실행 (ICollector 인터페이스)

        Args:
            context: 수집 컨텍스트
                - target_date: 수집 대상 날짜
                - options: {} (백준은 옵션 불필요)

        Returns:
            수집 결과 (CollectionResult)
        """
        try:
            result_dict = self.collect_baekjoon(context.target_date)

            return CollectionResult(
                success=result_dict['success'],
                date=context.target_date,
                items_count=result_dict['solutions_count'],
                artifact_ids=result_dict['artifact_ids'],
                metadata={'source': 'baekjoon'},
                error=result_dict.get('error')
            )

        except Exception as e:
            logger.error(f"백준 수집 실패: {e}")
            return CollectionResult(
                success=False,
                date=context.target_date,
                items_count=0,
                artifact_ids=[],
                metadata={'source': 'baekjoon'},
                error=str(e)
            )

    def should_run(self, context: CollectionContext) -> bool:
        """
        수집 실행 여부 판단 (ICollector 인터페이스)

        Args:
            context: 수집 컨텍스트

        Returns:
            항상 True (백준은 매일 수집)
        """
        return True

    def get_name(self) -> str:
        """
        Collector 이름 반환 (ICollector 인터페이스)

        Returns:
            "baekjoon"
        """
        return "baekjoon"

    # ============================================
    # 편의 메서드 (기존 호환성 유지)
    # ============================================

    def collect_baekjoon(self, target_date: date = None) -> Dict:
        """
        백준 데이터 수집 + 파싱 + 저장

        Returns:
            {
                'success': bool,
                'date': date,
                'solutions_count': int,
                'artifact_ids': List[int]
            }
        """
        target_date = target_date or date.today()
        logger.info(f"백준 데이터 수집 시작: {target_date}")

        try:
            # 1. Export - 백준허브 연동 레포에서 당일 제출 문제 수집
            logger.info("[1/3] 백준허브 연동 레포에서 백준 제출 수집...")
            problems = self.exporter.export_today(target_date)

            if not problems:
                logger.info("당일 제출된 문제가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'solutions_count': 0,
                    'artifact_ids': []
                }

            # 2. Parse - README.md 및 코드 파일 파싱
            logger.info(f"[2/3] {len(problems)}개 문제 파싱...")
            parsed_problems = self.parser.parse_problems(problems, self.exporter)

            if not parsed_problems:
                logger.warning("파싱된 문제가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'solutions_count': 0,
                    'artifact_ids': []
                }

            # 3. Save - DB 저장
            logger.info("[3/3] DB에 저장...")
            artifact_ids = self.saver.save_all(parsed_problems, target_date)

            logger.info(f"백준 수집 완료: {len(artifact_ids)}개 저장")

            return {
                'success': True,
                'date': target_date,
                'solutions_count': len(parsed_problems),
                'artifact_ids': artifact_ids
            }

        except Exception as e:
            logger.error(f"백준 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'solutions_count': 0,
                'artifact_ids': [],
                'error': str(e)
            }
