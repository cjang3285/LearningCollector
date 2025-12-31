#!/usr/bin/env python3
"""
Claude Migration Collector - Claude ZIP 마이그레이션

첫 이용 시 Claude.ai ZIP 파일을 마크다운으로 변환 후
ai_chat_collector를 통해 저장합니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date, datetime, timezone
from typing import List, Dict
import logging
import tempfile

from bulk_import.claude_parse import ClaudeMigrationParser
from bulk_import.zip_finder import ClaudeZipFinder
from parse.ai_chat_parse import AIMarkdownParser
from storage.ai_chat_saver import AIChatSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_migration')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeMigrationCollector:
    """Claude ZIP → 마크다운 → DB 마이그레이션"""

    def __init__(self):
        self.migration_parser = ClaudeMigrationParser()
        self.markdown_parser = AIMarkdownParser()
        self.saver = AIChatSaver()

    def collect(self, zip_path: str = None, target_date: date = None, all_dates: bool = False) -> Dict:
        """
        Claude ZIP 파일 마이그레이션

        Args:
            zip_path: Claude.ai에서 다운로드한 ZIP 파일 (None이면 자동 감지)
            target_date: 저장할 날짜 (기본값: 오늘)
            all_dates: True면 모든 대화 수집, False면 target_date만

        Returns:
            {
                'success': bool,
                'date': date,
                'conversations_count': int,
                'artifact_ids': List[int]
            }
        """
        target_date = target_date or date.today()

        # ZIP 파일 자동 감지
        if not zip_path:
            logger.info("ZIP 파일 경로가 지정되지 않음, 자동 감지 시작...")
            finder = ClaudeZipFinder()
            zip_file = finder.find_latest_zip()

            if not zip_file:
                raise ValueError("Claude ZIP 파일을 찾을 수 없습니다. 경로를 직접 지정하거나 ~/Downloads 또는 ../shared에 ZIP 파일을 배치하세요.")

            zip_path = str(zip_file)
            logger.info(f"자동 감지된 ZIP 파일: {zip_path}")

        logger.info(f"Claude ZIP 마이그레이션 시작: {zip_path}")
        logger.info(f"전체 수집 모드: {all_dates}")

        try:

            # 1. ZIP → 마크다운 변환
            logger.info("[1/3] ZIP 파일을 마크다운으로 변환...")
            markdowns = self.migration_parser.parse_zip(zip_path)

            if not markdowns:
                logger.info("ZIP 파일에 대화가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': []
                }

            # 2. 날짜 필터링 (all_dates=False인 경우)
            if not all_dates:
                today_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                today_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

                markdowns = self.migration_parser.filter_by_date(
                    markdowns,
                    after=today_start,
                    before=today_end
                )

                if not markdowns:
                    logger.info(f"{target_date}에 해당하는 대화가 없습니다.")
                    return {
                        'success': True,
                        'date': target_date,
                        'conversations_count': 0,
                        'artifact_ids': []
                    }

            logger.info(f"마이그레이션할 대화: {len(markdowns)}개")

            # 3. 마크다운 → AI Chat 파싱 (ai_chat_parse.py 사용)
            logger.info("[2/3] 마크다운 파싱...")

            # 임시 파일로 저장하여 ai_chat_parse가 파싱
            conversations = []
            with tempfile.TemporaryDirectory() as tmpdir:
                for i, md_content in enumerate(markdowns):
                    # 임시 파일 생성
                    tmp_file = Path(tmpdir) / f"claude_migration_{i}.md"
                    with open(tmp_file, 'w', encoding='utf-8') as f:
                        f.write(md_content)

                    # ai_chat_parse로 파싱
                    try:
                        parsed = self.markdown_parser.parse_file(str(tmp_file))
                        conversations.append(parsed)
                    except Exception as e:
                        logger.error(f"마크다운 파싱 실패 ({i}): {e}")
                        continue

            if not conversations:
                logger.warning("파싱된 대화가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': []
                }

            # 4. DB 저장
            logger.info(f"[3/3] DB에 저장... ({len(conversations)}개)")
            conversation_dicts = [conv.to_dict() for conv in conversations]
            artifact_ids = self.saver.save_all(conversation_dicts, target_date)

            logger.info(f"Claude 마이그레이션 완료: {len(artifact_ids)}개 저장")

            # DB 저장 결과 상세 출력
            self._log_saved_conversations(conversations, artifact_ids)

            return {
                'success': True,
                'date': target_date,
                'conversations_count': len(conversations),
                'artifact_ids': artifact_ids
            }

        except Exception as e:
            logger.error(f"Claude 마이그레이션 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'error': str(e)
            }

    def _log_saved_conversations(self, conversations: List, artifact_ids: List[int]) -> None:
        """
        DB에 저장된 대화 결과를 로그로 출력.

        Args:
            conversations: 저장된 대화 객체 리스트
            artifact_ids: DB artifact ID 리스트
        """
        try:
            logger.info("=" * 60)
            logger.info("DB 저장 결과:")
            logger.info(f"  저장된 대화 수: {len(artifact_ids)}")
            logger.info("")

            # 각 대화별 상세 정보 (최대 5개만)
            display_count = min(5, len(conversations))
            for i in range(display_count):
                conv = conversations[i]
                artifact_id = artifact_ids[i] if i < len(artifact_ids) else None

                logger.info(f"  [{i+1}] {conv.title}")
                logger.info(f"      - Artifact ID: {artifact_id}")
                logger.info(f"      - Provider: {conv.provider}")
                logger.info(f"      - 메시지 수: {conv.total_messages} ({conv.user_messages} user, {conv.assistant_messages} assistant)")
                logger.info(f"      - 코드 포함: {'예' if conv.has_code else '아니오'}")
                logger.info(f"      - Created: {conv.created_at}")
                logger.info("")

            if len(conversations) > 5:
                logger.info(f"  ... (나머지 {len(conversations) - 5}개 대화 생략)")

            logger.info("=" * 60)

        except Exception as e:
            logger.debug(f"저장 결과 출력 실패: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Claude ZIP 마이그레이션',
        epilog='ZIP 경로를 지정하지 않으면 자동으로 최신 ZIP 파일을 찾습니다.'
    )
    parser.add_argument(
        'zip_path',
        nargs='?',  # Optional positional argument
        default=None,
        help='Claude ZIP 파일 경로 (생략 시 자동 감지)'
    )
    parser.add_argument('--all', action='store_true', help='모든 대화 마이그레이션')
    parser.add_argument('--date', help='대상 날짜 (YYYY-MM-DD)')

    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    collector = ClaudeMigrationCollector()
    result = collector.collect(args.zip_path, target_date, all_dates=args.all)

    print(f"\n결과: {result}")
