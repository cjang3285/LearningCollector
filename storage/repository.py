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

    마지막 수집 실행 날짜를 기준으로 다음날부터 오늘까지 범위를 계산.
    커밋이 0개여도 수집 실행 기록이 있으면 그 날짜를 기준으로 함.

    Args:
        source_type: 소스 타입
        default_days_back: 수집 이력이 없을 때 과거 며칠부터 수집할지

    Returns:
        (start_date, end_date) 튜플
    """
    today = date.today()

    # 마지막 수집 실행 날짜 조회 (커밋 0개여도 기록됨)
    last_run_date = get_last_collection_run_date(source_type)

    if last_run_date:
        start_date = last_run_date + timedelta(days=1)
        logger.debug(f"[{source_type}] 마지막 수집 실행: {last_run_date}, 다음 수집 시작: {start_date}")
    else:
        # 수집 실행 이력이 없으면 artifact_date 기준으로 조회 (하위 호환)
        last_artifact_date = get_last_collection_date(source_type)

        if last_artifact_date:
            start_date = last_artifact_date + timedelta(days=1)
            logger.info(f"[{source_type}] 마지막 데이터 날짜: {last_artifact_date}, 다음 수집 시작: {start_date}")
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


def update_collection_run(source_type: str, run_date: date, items_count: int = 0, success: bool = True) -> bool:
    """
    수집 실행 기록 업데이트

    커밋이 0개여도 수집을 시도했다는 사실을 기록하여
    다음 실행 시 올바른 날짜 범위를 계산할 수 있도록 함.

    Args:
        source_type: 소스 타입 (github, baekjoon 등)
        run_date: 수집한 날짜
        items_count: 수집한 아이템 수
        success: 성공 여부

    Returns:
        성공 여부
    """
    db_config = get_db_config()
    try:
        conn = get_connection(db_config)
        with conn.cursor() as cur:
            # learning_collection_runs 테이블에 기록
            # 테이블이 없으면 생성
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS learning.learning_collection_runs (
                    id SERIAL PRIMARY KEY,
                    source_type VARCHAR(50) NOT NULL,
                    run_date DATE NOT NULL,
                    items_count INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_type, run_date)
                )
                """
            )

            # 수집 기록 삽입 (중복 시 업데이트)
            cur.execute(
                """
                INSERT INTO learning.learning_collection_runs
                    (source_type, run_date, items_count, success)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source_type, run_date)
                DO UPDATE SET
                    items_count = EXCLUDED.items_count,
                    success = EXCLUDED.success,
                    created_at = CURRENT_TIMESTAMP
                """,
                (source_type, run_date, items_count, success),
            )

            conn.commit()
            logger.info(f"[{source_type}] 수집 기록 업데이트: {run_date} ({items_count}개)")
            return True

    except Exception as e:
        logger.error(f"수집 기록 업데이트 실패 ({source_type}, {run_date}): {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_last_collection_run_date(source_type: str) -> Optional[date]:
    """
    마지막 수집 실행 날짜 조회 (실제 데이터 유무와 무관)

    Args:
        source_type: 소스 타입

    Returns:
        마지막 수집 실행 날짜
    """
    db_config = get_db_config()
    try:
        conn = get_connection(db_config)
        with conn.cursor() as cur:
            # 테이블 존재 확인
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'learning'
                    AND table_name = 'learning_collection_runs'
                )
                """
            )

            table_exists = cur.fetchone()[0]

            if not table_exists:
                logger.info(f"[{source_type}] learning_collection_runs 테이블 없음 (첫 실행)")
                return None

            cur.execute(
                """
                SELECT MAX(run_date)
                FROM learning.learning_collection_runs
                WHERE source_type = %s
            """,
                (source_type,),
            )

            result = cur.fetchone()
            last_date = result[0] if result else None

            if last_date:
                logger.info(f"[{source_type}] 마지막 수집 실행 날짜: {last_date}")
            else:
                logger.info(f"[{source_type}] 수집 실행 이력 없음")

            return last_date

    except Exception as e:
        logger.error(f"마지막 수집 실행 날짜 조회 실패 ({source_type}): {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass
