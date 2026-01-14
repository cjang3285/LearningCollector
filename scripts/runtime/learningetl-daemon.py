#!/usr/bin/env python3
"""
개인 학습 정보 수집 데몬 - 파일 감지 및 자동 수집

AI_CHAT_DOWNLOAD_DIR 또는 ~/shared 폴더를 감시하여 새로운 파일이 생기면 자동으로 수집합니다.

Hot Reload:
- 코드 변경 감지 시 자동 재시작 (개발 편의성)
- HOT_RELOAD=false 환경변수로 비활성화 가능
"""

import os
import sys
import time
import logging
import signal
from pathlib import Path
from datetime import datetime, date
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_log_file
from config.logging_config import setup_logging
from main import LearningCollector

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('daemon'), __name__)


class CodeReloadHandler(FileSystemEventHandler):
    """코드 변경 감지 핸들러 (Hot Reload)"""

    def __init__(self):
        self.restart_requested = False

    def on_modified(self, event):
        """Python 파일 수정 감지"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Python 파일 수정 시 재시작
        if file_path.suffix == '.py':
            logger.info(f"[Hot Reload] 코드 변경 감지: {file_path.name}")
            logger.info("[Hot Reload] 3초 후 자동 재시작...")
            time.sleep(3)  # 파일 저장 완료 대기
            self.restart_requested = True


class LearningFileHandler(FileSystemEventHandler):
    """파일 시스템 이벤트 핸들러"""

    def __init__(self, watch_dir: str):
        self.watch_dir = Path(watch_dir)
        self.collector = LearningCollector()
        self.processed_files = set()  # 중복 처리 방지
        self.last_run = None
        logger.info(f"[Daemon] 감시 폴더: {self.watch_dir}")

    def on_created(self, event):
        """새 파일 생성 시"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # 마크다운 파일만 처리 (AI 채팅)
        if file_path.suffix == '.md' and file_path not in self.processed_files:
            logger.info(f"[Daemon] 새 파일 감지: {file_path.name}")
            self.process_file(file_path)

    def process_file(self, file_path: Path):
        """파일 처리"""
        try:
            # 파일이 완전히 쓰여질 때까지 대기
            time.sleep(2)

            # AI 채팅 수집
            logger.info(f"[Daemon] 처리 중: {file_path.name}")
            result = self.collector.run(
                ai_chat_scan=True,
                ai_chat_download_dir=str(self.watch_dir),
                target_date=date.today()
            )

            self.processed_files.add(file_path)
            logger.info(f"[Daemon] 완료: {result}")

        except Exception as e:
            logger.error(f"[Daemon] 처리 실패 ({file_path.name}): {e}")

    def run_periodic_scan(self):
        """주기적 전체 스캔 (1시간마다)"""
        now = datetime.now()

        # 첫 실행 또는 1시간 경과
        if self.last_run is None or (now - self.last_run).seconds > 3600:
            logger.info("[Daemon] 주기적 전체 스캔 시작...")
            try:
                result = self.collector.run(
                    ai_chat_scan=True,
                    ai_chat_download_dir=str(self.watch_dir),
                    target_date=date.today()
                )
                logger.info(f"[Daemon] 전체 스캔 완료: {result}")
                self.last_run = now
            except Exception as e:
                logger.error(f"[Daemon] 전체 스캔 실패: {e}")


def main():
    """데몬 메인 함수"""
    # 감시 폴더 (환경변수 또는 홈 디렉토리 기반)
    from pathlib import Path
    default_watch_dir = str(Path.home() / 'shared')
    watch_dir = os.getenv('LEARNING_WATCH_DIR', default_watch_dir)
    hot_reload = os.getenv('HOT_RELOAD', 'true').lower() == 'true'

    if not Path(watch_dir).exists():
        logger.error(f"[Daemon] 감시 폴더가 존재하지 않습니다: {watch_dir}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("[Daemon] 개인 학습 정보 수집 데몬 시작")
    logger.info("=" * 60)
    if hot_reload:
        logger.info("[Daemon] Hot Reload: 활성화 (코드 변경 시 자동 재시작)")
    else:
        logger.info("[Daemon] Hot Reload: 비활성화")

    # 파일 핸들러 및 옵저버 설정
    event_handler = LearningFileHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=False)
    observer.start()

    # Hot Reload 설정 (코드 변경 감지)
    code_reload_handler = None
    code_observer = None
    if hot_reload:
        code_reload_handler = CodeReloadHandler()
        code_observer = Observer()
        # 프로젝트 루트의 Python 파일 감시
        for folder in ['collectors', 'parse', 'storage', 'config', 'scripts']:
            folder_path = PROJECT_ROOT / folder
            if folder_path.exists():
                code_observer.schedule(code_reload_handler, str(folder_path), recursive=True)
        code_observer.start()

    logger.info("[Daemon] 파일 감시 중... (Ctrl+C로 종료)")

    try:
        while True:
            # Hot Reload 체크
            if hot_reload and code_reload_handler and code_reload_handler.restart_requested:
                logger.info("[Daemon] 재시작 중...")
                observer.stop()
                if code_observer:
                    code_observer.stop()
                observer.join()
                if code_observer:
                    code_observer.join()

                # 프로세스 재시작 (systemd가 자동으로 재시작)
                os.execv(sys.executable, [sys.executable] + sys.argv)

            time.sleep(60)  # 1분마다 깨어남
            event_handler.run_periodic_scan()  # 주기적 스캔
    except KeyboardInterrupt:
        logger.info("[Daemon] 데몬 종료 중...")
        observer.stop()
        if code_observer:
            code_observer.stop()

    observer.join()
    if code_observer:
        code_observer.join()
    logger.info("[Daemon] 개인 학습 정보 수집 데몬 종료됨")


if __name__ == "__main__":
    main()
