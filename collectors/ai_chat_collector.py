#!/usr/bin/env python3
"""
AI Chat Collector - AI 채팅 마크다운 수집 + 파싱 + DB 저장

Claude, ChatGPT, Gemini 마크다운 내보내기 파일 처리
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from typing import List, Dict, Optional
import logging

from parse.ai_chat_parse import AIMarkdownParser
from storage.ai_chat_saver import AIChatSaver
from export.ai_chat_export import AIExportWatcher
from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('ai_chat_collector'), __name__)


class AIChatCollector:
    """AI 채팅 마크다운 수집 통합"""

    def __init__(self):
        self.parser = AIMarkdownParser()
        self.saver = AIChatSaver()

    def collect_from_files(
        self,
        file_paths: List[str],
        target_date: date = None
    ) -> Dict:
        """
        마크다운 파일 리스트에서 AI 채팅 수집

        Args:
            file_paths: 마크다운 파일 경로 리스트
            target_date: 저장할 날짜 (기본값: 오늘)

        Returns:
            {
                'success': bool,
                'date': date,
                'conversations_count': int,
                'artifact_ids': List[int],
                'providers': Dict[str, int]
            }
        """
        target_date = target_date or date.today()
        logger.info(f"AI 채팅 데이터 수집 시작: {target_date}")
        logger.info(f"파일 수: {len(file_paths)}개")

        try:
            # 1. Parse - 마크다운 파싱
            logger.info(f"[1/2] {len(file_paths)}개 파일 파싱...")
            conversations = self.parser.parse_multiple(file_paths)

            if not conversations:
                logger.info("파싱된 대화가 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': [],
                    'providers': {}
                }

            # 제공자별 통계
            providers = {}
            for conv in conversations:
                provider = conv.provider
                providers[provider] = providers.get(provider, 0) + 1

            logger.info(f"파싱 완료: {providers}")

            # ConversationData 객체를 딕셔너리로 변환
            conversation_dicts = [conv.to_dict() for conv in conversations]

            # 2. Save - DB 저장
            logger.info("[2/2] DB에 저장...")
            artifact_ids = self.saver.save_all(conversation_dicts, target_date)

            # 구체적인 수집 결과 출력
            logger.info("=" * 60)
            logger.info(f"📊 AI 채팅 수집 완료")
            logger.info(f"  📁 발견된 파일: {len(file_paths)}개")
            logger.info(f"  ✅ 파싱 성공: {len(conversations)}개")
            logger.info(f"  💾 DB 저장: {len(artifact_ids)}개")
            logger.info(f"  ⏭️  중복 스킵: {len(conversations) - len(artifact_ids)}개")
            logger.info("=" * 60)

            return {
                'success': True,
                'date': target_date,
                'conversations_count': len(conversations),
                'artifact_ids': artifact_ids,
                'providers': providers
            }

        except Exception as e:
            logger.error(f"AI 채팅 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'providers': {},
                'error': str(e)
            }

    def collect_from_downloads(
        self,
        download_dir: Optional[str] = None,
        target_date: date = None
    ) -> Dict:
        """
        다운로드 폴더에서 AI 채팅 파일 자동 수집

        Args:
            download_dir: 다운로드 폴더 경로 (기본값: ~/Downloads)
            target_date: 저장할 날짜 (기본값: 오늘)

        Returns:
            수집 결과 딕셔너리
        """
        target_date = target_date or date.today()
        logger.info("다운로드 폴더에서 AI 채팅 파일 스캔 중...")

        try:
            # Watcher로 기존 파일 스캔
            watcher = AIExportWatcher(download_dir=download_dir)
            ai_files = watcher.scan_existing()

            if not ai_files:
                logger.info("다운로드 폴더에 AI 채팅 파일이 없습니다.")
                return {
                    'success': True,
                    'date': target_date,
                    'conversations_count': 0,
                    'artifact_ids': [],
                    'providers': {}
                }

            # 파일 경로를 문자열로 변환
            file_paths = [str(f) for f in ai_files]

            # 파일 리스트로 수집
            return self.collect_from_files(file_paths, target_date)

        except Exception as e:
            logger.error(f"다운로드 폴더 스캔 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'date': target_date,
                'conversations_count': 0,
                'artifact_ids': [],
                'providers': {},
                'error': str(e)
            }

    def start_watcher(
        self,
        download_dir: Optional[str] = None,
        target_dir: Optional[str] = None
    ):
        """
        다운로드 폴더 실시간 감시 시작

        Args:
            download_dir: 감시할 다운로드 폴더
            target_dir: 파일 저장 폴더
        """
        logger.info("AI 채팅 파일 실시간 감시 시작...")

        def process_callback(file_path: Path):
            """파일 감지 시 자동 처리"""
            logger.info(f"새 파일 감지: {file_path.name}")
            try:
                result = self.collect_from_files([str(file_path)])
                logger.info(f"자동 수집 완료: {result}")
            except Exception as e:
                logger.error(f"자동 수집 실패: {e}")

        watcher = AIExportWatcher(
            download_dir=download_dir,
            target_dir=target_dir
        )

        # 콜백과 함께 감시 시작
        watcher.start(callback=process_callback)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='AI 채팅 마크다운 수집')
    parser.add_argument('files', nargs='*', help='마크다운 파일 경로')
    parser.add_argument('--download-dir', help='다운로드 폴더 경로')
    parser.add_argument('--watch', action='store_true', help='실시간 감시 모드')
    parser.add_argument('--scan', action='store_true', help='다운로드 폴더 스캔')

    args = parser.parse_args()

    collector = AIChatCollector()

    if args.watch:
        # 실시간 감시 모드
        print("\nAI 채팅 파일 실시간 감시 중... (Ctrl+C로 중지)")
        collector.start_watcher(download_dir=args.download_dir)
    elif args.scan:
        # 다운로드 폴더 스캔
        result = collector.collect_from_downloads(download_dir=args.download_dir)
        print(f"\n결과: {result}")
    elif args.files:
        # 파일 리스트 수집
        result = collector.collect_from_files(args.files)
        print(f"\n결과: {result}")
    else:
        print("사용법:")
        print("  python ai_chat_collector.py file1.md file2.md  # 파일 수집")
        print("  python ai_chat_collector.py --scan             # 다운로드 폴더 스캔")
        print("  python ai_chat_collector.py --watch            # 실시간 감시")
