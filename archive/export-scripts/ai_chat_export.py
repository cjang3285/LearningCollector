#!/usr/bin/env python3
"""
AI Chat Export - 다운로드 폴더 모니터링

AI 채팅 마크다운 파일 자동 감지 및 수집:
- Claude Exporter
- ChatGPT Exporter
- Gemini Exporter
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import shutil
import logging
from datetime import datetime
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('ai_chat_export')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AIMarkdownHandler(FileSystemEventHandler):
    """AI 채팅 마크다운 파일 감지 핸들러"""

    def __init__(self, download_dir: Path, target_dir: Path, callback=None):
        self.download_dir = Path(download_dir)
        self.target_dir = Path(target_dir)
        self.callback = callback

        # 감지할 파일 접두사
        self.prefixes = ['Claude-', 'ChatGPT-', 'Gemini-']

        # 타겟 디렉토리 생성
        self.target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AI 채팅 파일 모니터 초기화")
        logger.info(f"  감시 폴더: {self.download_dir}")
        logger.info(f"  저장 폴더: {self.target_dir}")

    def is_ai_chat_file(self, file_path: Path) -> bool:
        """AI 채팅 마크다운 파일인지 확인"""
        if file_path.suffix != '.md':
            return False

        return any(file_path.name.startswith(prefix) for prefix in self.prefixes)

    def process_file(self, file_path: Path):
        """파일 처리 (복사 및 콜백)"""
        try:
            # 파일이 완전히 쓰여질 때까지 대기 (다운로드 완료 보장)
            time.sleep(0.5)

            if not file_path.exists():
                logger.warning(f"파일이 존재하지 않음: {file_path}")
                return

            # 타임스탬프 추가하여 중복 방지
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            target_path = self.target_dir / new_name

            # 파일 복사
            shutil.copy2(file_path, target_path)
            logger.info(f"[OK] AI 채팅 파일 수집: {file_path.name} -> {new_name}")

            # 콜백 실행 (파싱 등)
            if self.callback:
                self.callback(target_path)

        except Exception as e:
            logger.error(f"파일 처리 실패 ({file_path.name}): {e}")

    def on_created(self, event):
        """파일 생성 이벤트"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self.is_ai_chat_file(file_path):
            logger.info(f"AI 채팅 파일 감지: {file_path.name}")
            self.process_file(file_path)

    def on_modified(self, event):
        """파일 수정 이벤트 (다운로드 완료 감지용)"""
        # 일부 브라우저는 다운로드 시 modified 이벤트 발생
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self.is_ai_chat_file(file_path):
            # created 이벤트에서 이미 처리되므로 스킵
            pass


class AIExportWatcher:
    """AI 채팅 내보내기 감시자"""

    def __init__(
        self,
        download_dir: Optional[str] = None,
        target_dir: Optional[str] = None
    ):
        # 기본 다운로드 폴더
        if download_dir is None:
            home = Path.home()
            download_dir = home / 'Downloads'

        # 기본 저장 폴더
        if target_dir is None:
            target_dir = PROJECT_ROOT / 'data' / 'ai_chats'

        self.download_dir = Path(download_dir)
        self.target_dir = Path(target_dir)

        if not self.download_dir.exists():
            raise ValueError(f"다운로드 폴더가 존재하지 않음: {self.download_dir}")

        self.observer = None

    def start(self, callback=None):
        """감시 시작"""
        event_handler = AIMarkdownHandler(
            self.download_dir,
            self.target_dir,
            callback
        )

        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.download_dir), recursive=False)
        self.observer.start()

        logger.info("[OK] AI 채팅 파일 감시 시작")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """감시 중지"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("AI 채팅 파일 감시 중지")

    def scan_existing(self) -> List[Path]:
        """기존 AI 채팅 파일 스캔"""
        ai_files = []

        prefixes = ['Claude-', 'ChatGPT-', 'Gemini-']

        for file_path in self.download_dir.glob('*.md'):
            if any(file_path.name.startswith(prefix) for prefix in prefixes):
                ai_files.append(file_path)

        logger.info(f"기존 AI 채팅 파일 {len(ai_files)}개 발견")
        return ai_files

    def collect_existing(self, callback=None) -> int:
        """기존 파일 수집"""
        ai_files = self.scan_existing()

        handler = AIMarkdownHandler(
            self.download_dir,
            self.target_dir,
            callback
        )

        for file_path in ai_files:
            handler.process_file(file_path)

        return len(ai_files)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='AI 채팅 마크다운 파일 자동 수집')
    parser.add_argument('--download-dir', help='다운로드 폴더 경로')
    parser.add_argument('--target-dir', help='저장 폴더 경로')
    parser.add_argument('--scan-only', action='store_true', help='기존 파일만 스캔')

    args = parser.parse_args()

    watcher = AIExportWatcher(
        download_dir=args.download_dir,
        target_dir=args.target_dir
    )

    if args.scan_only:
        # 기존 파일만 수집
        count = watcher.collect_existing()
        print(f"\n[완료] {count}개 파일 수집 완료")
    else:
        # 실시간 감시 시작
        print("\nAI 채팅 파일 감시 중... (Ctrl+C로 중지)")
        watcher.start()
