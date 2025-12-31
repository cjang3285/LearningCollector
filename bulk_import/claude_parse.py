#!/usr/bin/env python3
"""
Claude Migration Parser - Claude ZIP → 마크다운 어댑터

SOLID 원칙 기반 리팩토링:
- SRP: 각 클래스가 하나의 책임만 담당
- OCP: 확장 가능하도록 인터페이스 사용
- DIP: 구체 클래스가 아닌 추상화에 의존

새로운 아키텍처:
- ClaudeJsonParser: JSON 파싱 및 유니코드 처리
- ClaudeMessageFormatter: 마크다운 변환
- ClaudeZipConverter: 전체 프로세스 조율
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from datetime import datetime
from typing import List, Optional

from bulk_import.converters import ClaudeZipConverter
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


class ClaudeMigrationParser:
    """
    Claude ZIP 파일을 마크다운 형식으로 변환하는 어댑터.

    하위 호환성:
    - 기존 인터페이스 유지 (parse_zip, filter_by_date)
    - 내부 구현은 새로운 SOLID 아키텍처 사용
    """

    def __init__(self):
        """Initialize parser with SOLID-compliant converter."""
        self.converter = ClaudeZipConverter()

    def parse_zip(self, zip_path: str) -> List[str]:
        """
        ZIP 파일에서 대화들을 추출하여 마크다운 리스트로 변환.

        Args:
            zip_path: ZIP 파일 경로

        Returns:
            마크다운 문자열 리스트

        Raises:
            FileNotFoundError: ZIP 파일이 없을 때
            ValueError: ZIP이 유효하지 않을 때
        """
        return self.converter.convert_zip(zip_path)

    def filter_by_date(
        self,
        markdowns: List[str],
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> List[str]:
        """
        날짜로 마크다운 필터링.

        Args:
            markdowns: 마크다운 리스트
            after: 시작 날짜
            before: 종료 날짜

        Returns:
            필터링된 마크다운 리스트
        """
        return self.converter.filter_by_date(markdowns, after, before)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("사용법: python claude_parse.py <zip_file>")
        sys.exit(1)

    parser = ClaudeMigrationParser()
    markdowns = parser.parse_zip(sys.argv[1])

    print(f"\n변환된 마크다운 {len(markdowns)}개:")
    for i, md in enumerate(markdowns[:3], 1):
        print(f"\n[{i}] 미리보기:")
        print(md[:500] + "..." if len(md) > 500 else md)
