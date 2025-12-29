#!/usr/bin/env python3
"""
LearningETL Client Agent

노트북/데스크탑에서 실행:
    python client/agent.py --server http://raspberrypi.local:8000

기능:
    1. Downloads 폴더 실시간 감시
    2. AI 채팅 파일 감지 시 로컬 큐에 추가
    3. 주기적으로 큐에서 파일을 서버로 전송
"""

import os
import sys
from pathlib import Path
import time
import hashlib
import shutil
import logging
import argparse
import requests
from datetime import datetime
from typing import Optional, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIExportHandler(FileSystemEventHandler):
    """AI 채팅 파일 감지 핸들러"""

    AI_CHAT_PATTERNS = [
        'Claude-Export',
        'ChatGPT-Export',
        'Gemini-Chat',
        'claude.ai',
        'chatgpt',
        'gemini'
    ]

    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.pending_dir = queue_dir / "pending"
        self.pending_dir.mkdir(parents=True, exist_ok=True)

    def is_ai_chat_file(self, filename: str) -> bool:
        """AI 채팅 파일인지 확인"""
        filename_lower = filename.lower()
        return (
            filename.endswith('.md') and
            any(pattern.lower() in filename_lower for pattern in self.AI_CHAT_PATTERNS)
        )

    def on_created(self, event):
        """파일 생성 이벤트 처리"""
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            file_path = Path(event.src_path)

            if self.is_ai_chat_file(file_path.name):
                logger.info(f"AI 채팅 파일 감지: {file_path.name}")

                # 파일이 완전히 쓰여질 때까지 대기 (최대 5초)
                time.sleep(1)
                for _ in range(5):
                    try:
                        # 파일 읽기 시도
                        with open(file_path, 'r', encoding='utf-8') as f:
                            f.read(1)
                        break
                    except (PermissionError, IOError):
                        time.sleep(1)

                # 로컬 큐로 복사
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    queue_file = self.pending_dir / f"{timestamp}_{file_path.name}"
                    shutil.copy2(file_path, queue_file)
                    logger.info(f"로컬 큐에 추가: {queue_file.name}")
                except Exception as e:
                    logger.error(f"큐 추가 실패: {e}")


class FileUploader:
    """파일 업로드 관리"""

    def __init__(self, server_url: str, queue_dir: Path):
        self.server_url = server_url.rstrip('/')
        self.queue_dir = queue_dir
        self.pending_dir = queue_dir / "pending"
        self.sent_dir = queue_dir / "sent"
        self.failed_dir = queue_dir / "failed"

        # 디렉토리 생성
        self.sent_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def calculate_md5(self, file_path: Path) -> str:
        """파일 MD5 체크섬 계산"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def upload_file(self, file_path: Path) -> bool:
        """파일을 서버로 업로드"""
        try:
            # MD5 체크섬 계산
            md5 = self.calculate_md5(file_path)

            # 파일 업로드
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'text/markdown')}
                data = {'md5': md5}

                logger.info(f"파일 전송 중: {file_path.name} (MD5: {md5[:8]}...)")

                response = requests.post(
                    f"{self.server_url}/api/upload",
                    files=files,
                    data=data,
                    timeout=30
                )

                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    logger.info(f"전송 성공: {file_path.name}")
                    return True
                else:
                    logger.error(f"전송 실패: {result}")
                    return False

        except requests.exceptions.ConnectionError:
            logger.warning(f"서버 연결 실패: {self.server_url}")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"전송 타임아웃: {file_path.name}")
            return False
        except Exception as e:
            logger.error(f"전송 에러: {e}")
            import traceback
            traceback.print_exc()
            return False

    def process_queue(self):
        """큐에 있는 파일들을 서버로 전송"""
        pending_files = sorted(self.pending_dir.glob("*.md"))

        if pending_files:
            logger.info(f"전송 대기 중인 파일: {len(pending_files)}개")

        for file_path in pending_files:
            success = self.upload_file(file_path)

            if success:
                # 성공 → sent/ 로 이동
                sent_file = self.sent_dir / file_path.name
                shutil.move(str(file_path), str(sent_file))
                logger.info(f"백업 완료: {sent_file.name}")
            else:
                # 실패 → failed/ 로 이동 (나중에 재시도)
                failed_file = self.failed_dir / file_path.name
                if not failed_file.exists():
                    shutil.move(str(file_path), str(failed_file))
                    logger.warning(f"전송 실패 파일 보관: {failed_file.name}")

    def retry_failed(self):
        """실패한 파일 재시도"""
        failed_files = list(self.failed_dir.glob("*.md"))

        if failed_files:
            logger.info(f"실패 파일 재시도: {len(failed_files)}개")

            for file_path in failed_files:
                # pending으로 다시 이동
                pending_file = self.pending_dir / file_path.name
                shutil.move(str(file_path), str(pending_file))


class ClientAgent:
    """클라이언트 에이전트 메인"""

    def __init__(
        self,
        server_url: str,
        download_dir: Optional[Path] = None,
        queue_dir: Optional[Path] = None
    ):
        self.server_url = server_url

        # 기본 디렉토리 설정
        if download_dir is None:
            download_dir = Path.home() / "Downloads"
        if queue_dir is None:
            queue_dir = Path.home() / ".learningetl" / "queue"

        self.download_dir = download_dir
        self.queue_dir = queue_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        # 컴포넌트 초기화
        self.event_handler = AIExportHandler(self.queue_dir)
        self.uploader = FileUploader(server_url, self.queue_dir)
        self.observer = Observer()

    def check_server(self) -> bool:
        """서버 연결 확인"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            response.raise_for_status()
            logger.info(f"서버 연결 성공: {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"서버 연결 실패: {e}")
            return False

    def scan_existing_files(self):
        """다운로드 폴더에 기존 파일 스캔"""
        logger.info(f"기존 파일 스캔 중: {self.download_dir}")

        for file_path in self.download_dir.glob("*.md"):
            if self.event_handler.is_ai_chat_file(file_path.name):
                # 이미 큐에 있는지 확인
                pending_file = self.queue_dir / "pending" / file_path.name
                if not pending_file.exists():
                    logger.info(f"기존 파일 발견: {file_path.name}")
                    try:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        queue_file = self.queue_dir / "pending" / f"{timestamp}_{file_path.name}"
                        shutil.copy2(file_path, queue_file)
                        logger.info(f"큐에 추가: {queue_file.name}")
                    except Exception as e:
                        logger.error(f"파일 복사 실패: {e}")

    def start(self):
        """에이전트 시작"""
        logger.info("="*60)
        logger.info("LearningETL Client Agent 시작")
        logger.info("="*60)
        logger.info(f"서버: {self.server_url}")
        logger.info(f"감시 폴더: {self.download_dir}")
        logger.info(f"큐 폴더: {self.queue_dir}")
        logger.info("="*60)

        # 서버 연결 확인
        if not self.check_server():
            logger.warning("서버에 연결할 수 없지만 로컬 큐에 파일을 저장합니다")

        # 기존 파일 스캔
        self.scan_existing_files()

        # 실패한 파일 재시도
        self.uploader.retry_failed()

        # 초기 큐 처리
        self.uploader.process_queue()

        # 파일 감시 시작
        self.observer.schedule(
            self.event_handler,
            str(self.download_dir),
            recursive=False
        )
        self.observer.start()
        logger.info("파일 감시 시작")

        try:
            # 주기적으로 큐 처리
            while True:
                time.sleep(10)  # 10초마다
                self.uploader.process_queue()

        except KeyboardInterrupt:
            logger.info("종료 신호 감지")
            self.observer.stop()

        self.observer.join()
        logger.info("에이전트 종료")


def main():
    parser = argparse.ArgumentParser(description='LearningETL Client Agent')
    parser.add_argument(
        '--server',
        type=str,
        required=True,
        help='서버 URL (예: http://raspberrypi.local:8000)'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        help='다운로드 폴더 경로 (기본값: ~/Downloads)'
    )
    parser.add_argument(
        '--queue-dir',
        type=str,
        help='큐 폴더 경로 (기본값: ~/.learningetl/queue)'
    )

    args = parser.parse_args()

    download_dir = Path(args.download_dir) if args.download_dir else None
    queue_dir = Path(args.queue_dir) if args.queue_dir else None

    agent = ClientAgent(
        server_url=args.server,
        download_dir=download_dir,
        queue_dir=queue_dir
    )

    agent.start()


if __name__ == '__main__':
    main()
