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

from db_savers.baekjoon_saver import BaekjoonSaver
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
            # 백준도 현재는 스킵 (추후 구현)
            logger.info("백준 수집은 현재 구현되지 않았습니다 (추후 구현 예정)")

            return {
                'success': True,
                'date': target_date,
                'solutions_count': 0,
                'artifact_ids': [],
                'message': 'Baekjoon collector not implemented yet'
            }

        except Exception as e:
            logger.error(f"백준 수집 실패: {e}")
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
