#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다운로드 폴더 감시 - Claude Export 자동 이동

사용자가 수동으로 Claude.ai Export를 클릭하면
다운로드 폴더에서 자동으로 감지하여 NAS로 이동

실행:
  python tools/watch_downloads.py

백그라운드 실행:
  pythonw tools/watch_downloads.py
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 설정
DOWNLOADS_DIR = Path(os.path.expanduser("~/Downloads"))
NAS_DIR = Path("Z:/learning-etl/claude-exports")
LOG_FILE = PROJECT_ROOT / 'logs' / 'download_watcher.log'
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ClaudeExportHandler(FileSystemEventHandler):
    """Claude Export 파일 감지 및 이동"""

    def __init__(self):
        self.processing = set()

    def on_created(self, event):
        """파일 생성 이벤트"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Claude Export 파일인지 확인
        # 패턴: data-YYYY-MM-DD-HH-MM-SS-batch-XXXX.zip
        if not file_path.suffix == '.zip':
            return

        filename = file_path.name.lower()

        # Claude export 패턴 확인
        is_claude_export = (
            'conversations_' in filename or
            'claude_' in filename or
            'data-' in filename  # data-2025-12-26-01-09-16-batch-0000.zip
        )

        if not is_claude_export:
            return

        # 이미 처리 중인지 확인
        if str(file_path) in self.processing:
            return

        logger.info(f"새 Export 파일 감지: {file_path.name}")
        self.processing.add(str(file_path))

        try:
            # 다운로드 완료 대기 (파일 크기 안정화)
            self.wait_download_complete(file_path)

            # NAS로 이동
            self.move_to_nas(file_path)

        except Exception as e:
            logger.error(f"처리 실패: {e}", exc_info=True)
        finally:
            self.processing.discard(str(file_path))

    def wait_download_complete(self, file_path: Path, timeout=60):
        """다운로드 완료 대기

        Args:
            file_path: 파일 경로
            timeout: 최대 대기 시간 (초)
        """
        logger.info(f"  다운로드 완료 대기 중...")
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size

                if current_size == last_size and current_size > 0:
                    # 크기가 안정화됨 (다운로드 완료)
                    logger.info(f"  다운로드 완료: {current_size / 1024 / 1024:.2f} MB")
                    return

                last_size = current_size
                time.sleep(2)

            except FileNotFoundError:
                logger.warning(f"  파일이 사라짐: {file_path}")
                return

        logger.warning(f"  다운로드 대기 타임아웃")

    def move_to_nas(self, file_path: Path):
        """NAS로 파일 이동

        Args:
            file_path: 원본 파일 경로
        """
        # NAS 디렉토리 확인
        if not NAS_DIR.exists():
            logger.error(f"❌ NAS 디렉토리 없음: {NAS_DIR}")
            logger.info("  로컬 백업 디렉토리로 이동...")
            backup_dir = PROJECT_ROOT / 'temp' / 'claude-exports'
            backup_dir.mkdir(parents=True, exist_ok=True)
            destination_dir = backup_dir
        else:
            destination_dir = NAS_DIR

        # 타임스탬프 추가하여 충돌 방지
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 원본 파일명에서 확장자 분리
        stem = file_path.stem
        suffix = file_path.suffix

        # 새 파일명 (타임스탬프 추가)
        if 'conversations_' in stem:
            # conversations_2024-12-27.zip → claude_export_20241227_123456.zip
            final_name = f"claude_export_{timestamp}{suffix}"
        elif 'data-' in stem:
            # data-2025-12-26-01-09-16-batch-0000.zip → claude_export_20241227_123456.zip
            final_name = f"claude_export_{timestamp}{suffix}"
        else:
            # 기타 패턴은 원본명 유지 + 타임스탬프
            final_name = f"{stem}_{timestamp}{suffix}"

        destination = destination_dir / final_name

        try:
            # 파일 이동
            shutil.move(str(file_path), str(destination))
            logger.info(f"✅ 이동 완료: {destination}")

            # 성공 알림 (선택)
            self.notify_success(destination)

        except Exception as e:
            logger.error(f"❌ 이동 실패: {e}")
            raise

    def notify_success(self, file_path: Path):
        """완료 알림 (선택)

        Args:
            file_path: 저장된 파일 경로
        """
        # Windows 알림 (선택)
        if sys.platform == 'win32':
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    "Claude Export 완료",
                    f"파일 저장: {file_path.name}",
                    duration=5,
                    threaded=True
                )
            except ImportError:
                # win10toast가 없으면 스킵
                pass


def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("Claude Export 다운로드 감시 시작")
    logger.info("=" * 60)
    logger.info(f"감시 디렉토리: {DOWNLOADS_DIR}")
    logger.info(f"저장 디렉토리: {NAS_DIR}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("다음 파일을 감지합니다:")
    logger.info("  - conversations_*.zip")
    logger.info("  - claude_*.zip")
    logger.info("  - data-YYYY-MM-DD-*.zip")
    logger.info("")
    logger.info("종료: Ctrl+C")
    logger.info("")

    # 감시 시작
    event_handler = ClaudeExportHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DOWNLOADS_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("종료 중...")
        observer.stop()

    observer.join()
    logger.info("종료됨")


if __name__ == '__main__':
    main()
