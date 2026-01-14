#!/usr/bin/env python3
"""
Repository shim — DB helper functions implemented here.

This module provides higher-level DB helpers for collectors and hides
the underlying connection implementation. Use this instead of
directly importing `storage.db_utils` in new code. Existing callers
can still use `storage.db_utils` (deprecated wrapper).
"""
from typing import Optional
from datetime import date, timedelta
import logging

from storage.db_client import get_connection
from config.settings import get_db_config

logger = logging.getLogger(__name__)


def get_last_collection_date(source_type: str) -> Optional[date]:
    db_config = get_db_config()
    try:
        conn = get_connection(db_config)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(artifact_date)
                FROM learning.learning_artifacts
                WHERE source_type = %s
            """,
                (source_type,),
            )

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
        try:
            conn.close()
        except Exception:
            pass


def get_collection_date_range(source_type: str, default_days_back: int = 7) -> tuple[date, date]:
    """
    수집할 날짜 범위 계산

    마지막 수집 날짜를 기준으로 다음날부터 오늘까지 범위를 계산.

    Args:
        source_type: 소스 타입
        default_days_back: 수집 이력이 없을 때 과거 며칠부터 수집할지

    Returns:
        (start_date, end_date) 튜플
    """
    today = date.today()
    last_date = get_last_collection_date(source_type)

    if last_date:
        start_date = last_date + timedelta(days=1)
        logger.info(f"[{source_type}] 마지막 수집 날짜: {last_date}, 다음 수집 시작: {start_date}")
    else:
        start_date = today - timedelta(days=default_days_back)
        logger.info(f"[{source_type}] 첫 실행, {default_days_back}일 전부터 수집: {start_date}")

    if start_date > today:
        logger.info(f"[{source_type}] 수집할 데이터 없음 (이미 최신)")
        return (today, today - timedelta(days=1))

    logger.info(f"[{source_type}] 수집 범위: {start_date} ~ {today}")
    return (start_date, today)


def has_data_for_date(source_type: str, target_date: date) -> bool:
    db_config = get_db_config()
    try:
        conn = get_connection(db_config)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM learning.learning_artifacts
                WHERE source_type = %s AND artifact_date = %s
            """,
                (source_type, target_date),
            )

            count = cur.fetchone()[0]
            return count > 0

    except Exception as e:
        logger.error(f"데이터 존재 확인 실패 ({source_type}, {target_date}): {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass
