#!/usr/bin/env python3
"""
Claude Collector - Claude 데이터 수집 + 파싱 + DB 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from typing import List, Dict
import logging

from db_savers.claude_saver import ClaudeSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_collector')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeCollector:
    """Claude 데이터 수집 통합"""

    def __init__(self):
        self.saver = ClaudeSaver()

    def collect(self, target_date: date = None) -> Dict:
        """
        Claude 데이터 수집 + 파싱 + 저장

        Returns:
            {
                'success': bool,
                'date': date,
                'conversations_count': int,
                'artifact_ids': List[int]
            }
        """
        target_date = target_date or date.today()
        logger.info(f"Claude 데이터 수집 시작: {target_date}")

        try:
            # Claude는 수동 Export가 필요하므로 현재는 스킵
            logger.info("Claude 수집은 현재 구현되지 않았습니다 (수동 Export 필요)")

            return {
                'success': True,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'message': 'Claude export requires manual operation'
            }

        except Exception as e:
            logger.error(f"Claude 수집 실패: {e}")
            return {
                'success': False,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'error': str(e)
            }


if __name__ == '__main__':
    collector = ClaudeCollector()
    result = collector.collect()
    print(f"\n결과: {result}")
