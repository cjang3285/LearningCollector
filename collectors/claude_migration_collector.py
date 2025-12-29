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

from storage.claude_migration_saver import ClaudeMigrationSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_migration_collector')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeMigrationCollector:
    """Claude ZIP 마이그레이션 수집기 (첫 이용 시 전체 대화 마이그레이션용)"""

    def __init__(self):
        self.saver = ClaudeMigrationSaver()

    def collect(self, zip_path: str, target_date: date = None, all_dates: bool = False) -> Dict:
        """
        Claude 데이터 수집 + 파싱 + 저장

        Args:
            zip_path: Claude.ai에서 수동으로 다운로드한 ZIP 파일 경로
            target_date: 수집할 날짜 (기본값: 오늘)

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
        logger.info(f"전체 수집 모드: {all_dates}")

        try:
            if not zip_path:
                logger.error("ZIP 파일 경로가 제공되지 않았습니다.")
                return {
                    'success': False,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': [],
                    'error': 'ZIP 파일 경로 필요'
                }

            # 1. Parse - ZIP 파일 파싱
            from parse.claude_migration_parse import ClaudeMigrationParser
            parser = ClaudeMigrationParser()

            logger.info(f"[1/2] ZIP 파일 파싱: {zip_path}")
            all_conversations = parser.parse_zip(zip_path)

            # 날짜 필터링
            from datetime import datetime, timezone
            today_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

            # 날짜 필터링 (all_dates=True면 스킵)
            if all_dates:
                filtered_conversations = [c for c in all_conversations if len(c.get('chat_messages', [])) >= 2]
                logger.info(f"전체 대화 수집 모드: {len(filtered_conversations)}개 대화")
            else:
                filtered_conversations = parser.filter_by_date(
                    all_conversations,
                    after=today_start,
                    before=today_end,
                    min_messages=2
                )

            if not filtered_conversations:
                logger.info(f"{target_date}에 해당하는 대화가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': []
                }

            # 파싱된 대화 데이터 생성
            parsed_conversations = [
                parser.parse_conversation(conv)
                for conv in filtered_conversations
            ]

            # 2. Save - DB 저장
            logger.info(f"[2/2] DB에 저장... ({len(parsed_conversations)}개)")
            artifact_ids = self.saver.save_all(
                [conv.to_dict() for conv in parsed_conversations],
                target_date
            )

            logger.info(f"Claude 수집 완료: {len(artifact_ids)}개 저장")

            return {
                'success': True,
                'date': target_date,
                'conversations_count': len(parsed_conversations),
                'artifact_ids': artifact_ids
            }

        except Exception as e:
            logger.error(f"Claude 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'error': str(e)
            }


if __name__ == '__main__':
    collector = ClaudeMigrationCollector()
    result = collector.collect()
    print(f"\n결과: {result}")
