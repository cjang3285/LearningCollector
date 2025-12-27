#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Export 파일 모니터링 (Pi)

NAS 또는 로컬 디렉토리를 감시하여
새 claude_export_*.zip 파일이 생기면 자동으로 파싱 및 DB 저장

실행:
  python tools/monitor_claude_exports.py

백그라운드 실행:
  nohup python tools/monitor_claude_exports.py > logs/export_monitor.log 2>&1 &
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CLAUDE_DOWNLOAD_DIR

# 로그 설정
LOG_FILE = PROJECT_ROOT / 'logs' / 'export_monitor.log'
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 감시할 디렉토리 (NAS 마운트 경로 또는 temp)
WATCH_DIR = PROJECT_ROOT / 'claude-exports'  # NAS: /mnt/nas/learning-etl/claude-exports
WATCH_DIR.mkdir(parents=True, exist_ok=True)

# 처리 완료 파일 기록
PROCESSED_FILE = PROJECT_ROOT / 'temp' / 'processed_exports.txt'
PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)

# 체크 간격 (초)
CHECK_INTERVAL = 60  # 1분마다


def load_processed_files():
    """이미 처리한 파일 목록 로드"""
    if not PROCESSED_FILE.exists():
        return set()

    with open(PROCESSED_FILE, 'r') as f:
        return set(line.strip() for line in f)


def mark_as_processed(filename):
    """파일을 처리 완료로 표시"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{filename}\n")


def process_export_file(export_file: Path):
    """Export ZIP 파일 파싱 및 DB 저장

    Args:
        export_file: claude_export_*.zip 파일 경로

    Returns:
        성공 여부
    """
    logger.info(f"처리 시작: {export_file.name}")

    try:
        # parse/claude_parse.py import
        from parse.claude_parse import ClaudeParser
        from collectors.claude_collector import ClaudeCollector

        # 파서 초기화
        parser = ClaudeParser()

        # ZIP 파싱
        logger.info("  ZIP 파일 파싱 중...")
        all_conversations = parser.parse_zip(export_file)
        logger.info(f"  {len(all_conversations)}개 대화 발견")

        # 증분 필터링 (이미 DB에 있는 대화 스킵)
        logger.info("  증분 필터링 중...")
        new_conversations = filter_new_conversations(all_conversations)
        logger.info(f"  {len(new_conversations)}개 새 대화")

        if not new_conversations:
            logger.info("  새로운 대화 없음")
            return True

        # DB 저장
        logger.info("  DB 저장 중...")
        from db_savers.claude_saver import ClaudeSaver

        saver = ClaudeSaver()
        artifact_ids = saver.save_conversations(new_conversations)

        logger.info(f"✅ 저장 완료: {len(artifact_ids)}개 아티팩트")
        return True

    except Exception as e:
        logger.error(f"❌ 처리 실패: {e}", exc_info=True)
        return False


def filter_new_conversations(conversations):
    """이미 DB에 있는 대화 제외

    Args:
        conversations: 모든 대화 목록

    Returns:
        새로운 대화 목록
    """
    try:
        from config.settings import get_db_config
        import psycopg2

        conn = psycopg2.connect(**get_db_config())
        cursor = conn.cursor()

        new_convs = []

        for conv in conversations:
            conv_uuid = conv.get('uuid')
            if not conv_uuid:
                continue

            # DB에 이미 있는지 확인
            cursor.execute("""
                SELECT 1
                FROM learning.claude_conversations
                WHERE conversation_uuid = %s
                LIMIT 1
            """, (conv_uuid,))

            if cursor.fetchone():
                # 이미 있음 - 스킵
                continue

            new_convs.append(conv)

        conn.close()
        return new_convs

    except Exception as e:
        logger.warning(f"증분 필터링 실패 (모든 대화 처리): {e}")
        # 에러 시 모든 대화 반환
        return conversations


def monitor_loop():
    """무한 루프로 디렉토리 감시"""
    logger.info("=" * 60)
    logger.info("Claude Export 모니터링 시작")
    logger.info(f"감시 디렉토리: {WATCH_DIR}")
    logger.info(f"체크 간격: {CHECK_INTERVAL}초")
    logger.info("=" * 60)

    processed_files = load_processed_files()
    logger.info(f"이미 처리한 파일: {len(processed_files)}개")

    while True:
        try:
            # ZIP 파일 찾기
            export_files = list(WATCH_DIR.glob("claude_export_*.zip"))

            # 새 파일만 필터링
            new_files = [f for f in export_files if f.name not in processed_files]

            if new_files:
                logger.info(f"새 파일 {len(new_files)}개 발견")

                for export_file in sorted(new_files, key=lambda x: x.stat().st_mtime):
                    logger.info(f"")
                    logger.info(f"{'='*60}")

                    # 파일 크기 확인 (다운로드 완료 대기)
                    initial_size = export_file.stat().st_size
                    time.sleep(2)
                    final_size = export_file.stat().st_size

                    if initial_size != final_size:
                        logger.info(f"  아직 다운로드 중... (대기)")
                        continue

                    # 처리 실행
                    success = process_export_file(export_file)

                    if success:
                        mark_as_processed(export_file.name)
                        processed_files.add(export_file.name)
                        logger.info(f"✅ 처리 완료: {export_file.name}")
                    else:
                        logger.error(f"❌ 처리 실패: {export_file.name}")

            # 다음 체크까지 대기
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\n종료 중...")
            break
        except Exception as e:
            logger.error(f"모니터링 에러: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


def main():
    """메인 함수"""
    if not WATCH_DIR.exists():
        logger.error(f"❌ 감시 디렉토리가 없습니다: {WATCH_DIR}")
        logger.info("디렉토리를 생성합니다...")
        WATCH_DIR.mkdir(parents=True, exist_ok=True)

    monitor_loop()


if __name__ == '__main__':
    main()
