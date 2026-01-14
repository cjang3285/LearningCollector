#!/usr/bin/env python3
"""
DB Utility Functions - 공통 DB 조회 헬퍼 함수들
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
from typing import Optional
from datetime import date, timedelta
import logging

from storage import collection_tracker

logger = logging.getLogger(__name__)


def _warn_deprecated():
    warnings.warn(
        "storage.db_utils is deprecated — use storage.collection_tracker or BaseSaver instead",
        DeprecationWarning,
        stacklevel=3,
    )


def get_last_collection_date(source_type: str) -> Optional[date]:
    _warn_deprecated()
    return collection_tracker.get_last_collection_date(source_type)


def get_collection_date_range(source_type: str, default_days_back: int = 7) -> tuple[date, date]:
    _warn_deprecated()
    return collection_tracker.get_collection_date_range(source_type, default_days_back=default_days_back)


def has_data_for_date(source_type: str, target_date: date) -> bool:
    _warn_deprecated()
    return collection_tracker.has_data_for_date(source_type, target_date)


if __name__ == '__main__':
    # 테스트
    print("=== DB Utils 테스트 ===\n")

    for source in ['github', 'baekjoon', 'ai_chat_claude']:
        print(f"\n[{source}]")
        last_date = get_last_collection_date(source)
        print(f"  마지막 수집: {last_date}")

        start, end = get_collection_date_range(source, default_days_back=7)
        print(f"  수집 범위: {start} ~ {end}")

        if last_date:
            has_data = has_data_for_date(source, last_date)
            print(f"  {last_date} 데이터 존재: {has_data}")
