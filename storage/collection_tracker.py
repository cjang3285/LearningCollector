#!/usr/bin/env python3
"""
Collection Tracker — 수집 상태 추적 모듈

수집 날짜 범위 계산 및 마지막 수집 날짜 추적 기능 제공.
파일 기반 추적을 우선 사용하고, 없으면 DB 조회로 fallback.
"""
from typing import Optional
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import re
import json

from storage.db_client import get_connection
from config.settings import get_db_config

logger = logging.getLogger(__name__)

# 프로젝트 루트 및 로그 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / 'logs'


def get_last_collection_date_from_files() -> Optional[date]:
    """
    로그 파일에서 마지막 수집 날짜 추출

    collect_result_*.json 파일을 우선 탐색하고, 없으면 etl_result_*.json도 탐색 (하위 호환).
    파일명에서 날짜를 추출하여 가장 최근 날짜를 반환.

    Returns:
        가장 최근 수집 날짜 (파일이 없으면 None)
    """
    if not LOGS_DIR.exists():
        logger.debug("로그 디렉토리가 존재하지 않음")
        return None

    # 패턴: collect_result_YYYY-MM-DD.json 또는 etl_result_YYYY-MM-DD.json
    pattern = re.compile(r'(collect_result|etl_result)_(\d{4}-\d{2}-\d{2})\.json')

    dates = []
    for file in LOGS_DIR.glob('*.json'):
        match = pattern.match(file.name)
        if match:
            try:
                date_str = match.group(2)
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                dates.append(file_date)
            except ValueError:
                logger.warning(f"파일명에서 날짜 파싱 실패: {file.name}")
                continue

    if dates:
        last_date = max(dates)
        logger.info(f"로그 파일에서 마지막 수집 날짜 발견: {last_date}")
        return last_date

    logger.debug("로그 파일에서 수집 날짜를 찾을 수 없음")
    return None


def get_last_collection_date(source_type: str) -> Optional[date]:
    """
    마지막 수집 날짜 조회 (파일 우선, DB fallback)

    1. logs/ 폴더의 collect_result_*.json 또는 etl_result_*.json 파일에서 날짜 추출
    2. 파일이 없으면 DB의 learning_artifacts 테이블에서 조회

    Args:
        source_type: 소스 타입 (현재는 사용하지 않지만 하위 호환 유지)

    Returns:
        마지막 수집 날짜 (없으면 None)
    """
    # 1. 파일에서 조회 (우선)
    last_date_from_files = get_last_collection_date_from_files()
    if last_date_from_files:
        logger.info(f"[{source_type}] 마지막 수집 날짜 (파일): {last_date_from_files}")
        return last_date_from_files

    # 2. DB에서 조회 (fallback)
    logger.debug(f"[{source_type}] 파일에서 날짜를 찾을 수 없어 DB 조회")
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
                logger.info(f"[{source_type}] 마지막 수집 날짜 (DB): {last_date}")
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
