#!/usr/bin/env python3
"""
Baekjoon Collector - 백준 데이터 수집 + 파싱 + DB 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from typing import List, Dict
import logging

from storage.baekjoon_saver import BaekjoonSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('baekjoon_collector')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaekjoonCollector:
    """백준 데이터 수집 통합"""

    def __init__(self):
        self.saver = BaekjoonSaver()

    def collect(self, target_date: date = None) -> Dict:
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
            # 1. Export - solved.ac API + Selenium으로 문제 풀이 수집
            from export.baekjoon_export import BaekjoonExporter
            exporter = BaekjoonExporter()

            logger.info("[1/3] 백준에서 오늘 푼 문제 수집...")
            problems = exporter.export_today()

            if not problems:
                logger.info("수집된 문제가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'solutions_count': 0,
                    'artifact_ids': []
                }

            # 2. Parse - 문제 데이터 파싱
            from parse.baekjoon_parse import BaekjoonParser
            parser = BaekjoonParser()

            logger.info(f"[2/3] {len(problems)}개 문제 파싱...")
            parsed_problems = parser.parse_problems(problems)

            # 3. Save - DB 저장
            logger.info(f"[3/3] DB에 저장... ({len(parsed_problems)}개)")
            artifact_ids = self.saver.save_all(
                [prob.to_dict() for prob in parsed_problems],
                target_date
            )

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


if __name__ == '__main__':
    collector = BaekjoonCollector()
    result = collector.collect()
    print(f"\n결과: {result}")
