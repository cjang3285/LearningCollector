#!/usr/bin/env python3
"""
백준 Collector - 백준 데이터 수집 + 파싱 + DB 저장

TIL 레포에서 크롬 확장 프로그램이 자동 푸시한 백준 풀이를 수집합니다.
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
        self.exporter = BaekjoonExporter()
        self.parser = BaekjoonParser()
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
            # 1. Export - TIL 레포에서 당일 제출 문제 수집
            logger.info("[1/3] TIL 레포에서 백준 제출 수집...")
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
            # Parser가 반환한 BaekjoonProblemData 객체를 딕셔너리로 변환
            problem_dicts = [p.to_dict() for p in parsed_problems]
            artifact_ids = self.saver.save_all(problem_dicts, target_date)

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
