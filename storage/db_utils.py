#!/usr/bin/env python3
"""
DB Utility Functions - 공통 DB 조회 헬퍼 함수들
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from datetime import date, timedelta
from typing import Optional
import logging

from config.settings import get_db_config

logger = logging.getLogger(__name__)


def get_last_collection_date(source_type: str) -> Optional[date]:
    """
    특정 소스의 마지막 수집 날짜 조회

    Args:
        source_type: 소스 타입 ('github', 'baekjoon', 'ai_chat_claude' 등)

    Returns:
        마지막 수집 날짜 또는 None (데이터 없음)
    """
    db_config = get_db_config()
    conn = None  # Initialize conn to None
    try:
        conn = psycopg2.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(artifact_date)
                FROM learning.learning_artifacts
                WHERE source_type = %s
            """, (source_type,))

            result = cur.fetchone()
            last_date = result[0] if result else None

            if last_date:
                logger.info(f"[{source_type}] 마지막 수집 날짜: {last_date}")
            else:
                logger.info(f"[{source_type}] 수집 이력 없음 (첫 실행)")

            return last_date

    except Exception as e:
        logger.error(f"마지막 수집 날짜 조회 실패 ({source_type}): {e}")
        return None

    finally:
        if conn:
            conn.close()


def get_collection_date_range(source_type: str, default_days_back: int = 7) -> tuple[date, date]:
    """
    증분 수집을 위한 날짜 범위 반환

    Args:
        source_type: 소스 타입
        default_days_back: 첫 실행 시 과거 며칠까지 수집할지 (기본: 7일)

    Returns:
        (시작 날짜, 종료 날짜) 튜플
        - 시작 날짜: 마지막 수집 날짜 + 1일 (또는 오늘-default_days_back)
        - 종료 날짜: 오늘
    """
    today = date.today()
    last_date = get_last_collection_date(source_type)

    if last_date:
        # 마지막 수집 다음 날부터
        start_date = last_date + timedelta(days=1)
    else:
        # 첫 실행: 과거 N일부터
        start_date = today - timedelta(days=default_days_back)

    # 시작 날짜가 오늘 이후면 수집할 것 없음
    if start_date > today:
        logger.info(f"[{source_type}] 수집할 데이터 없음 (이미 최신)")
        return (today, today - timedelta(days=1))  # 빈 범위

    logger.info(f"[{source_type}] 수집 범위: {start_date} ~ {today}")
    return (start_date, today)


def has_data_for_date(source_type: str, target_date: date) -> bool:
    """
    특정 날짜에 데이터가 이미 있는지 확인

    Args:
        source_type: 소스 타입
        target_date: 확인할 날짜

    Returns:
        데이터 존재 여부
    """
    db_config = get_db_config()
    conn = None  # Initialize conn to None
    try:
        conn = psycopg2.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM learning.learning_artifacts
                WHERE source_type = %s AND artifact_date = %s
            """, (source_type, target_date))

            count = cur.fetchone()[0]
            return count > 0

    except Exception as e:
        logger.error(f"데이터 존재 확인 실패 ({source_type}, {target_date}): {e}")
        return False

    finally:
        if conn:
            conn.close()


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
