#!/usr/bin/env python3
"""
공통 로깅 설정

stdout (daemon.log): INFO, WARNING 레벨
stderr (daemon-error.log): ERROR, CRITICAL 레벨
"""

import sys
import logging
from pathlib import Path


class StdoutFilter(logging.Filter):
    """WARNING 이하만 통과 (stdout용)"""
    def filter(self, record):
        return record.levelno <= logging.WARNING


class StderrFilter(logging.Filter):
    """ERROR 이상만 통과 (stderr용)"""
    def filter(self, record):
        return record.levelno >= logging.ERROR


def setup_logging(log_file_path: str, logger_name: str = None) -> logging.Logger:
    """
    표준 로깅 설정

    Args:
        log_file_path: 로그 파일 경로
        logger_name: 로거 이름 (기본값: __name__)

    Returns:
        설정된 Logger 객체
    """
    # stdout 핸들러 (INFO, WARNING)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.addFilter(StdoutFilter())
    stdout_handler.setLevel(logging.DEBUG)

    # stderr 핸들러 (ERROR, CRITICAL)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.addFilter(StderrFilter())
    stderr_handler.setLevel(logging.ERROR)

    # 파일 핸들러 (모든 레벨)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 로거 설정
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    # 상위 로거로 전파 방지
    logger.propagate = False

    return logger
