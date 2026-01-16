#!/usr/bin/env python3
"""
Collection Tracker - 수집 상태 추적 모듈 (파일 기반)

로그 파일을 사용하여 마지막 수집 날짜 추적 및 날짜 범위 계산
"""
from typing import Optional
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

# 프로젝트 루트 및 로그 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / 'logs'


def get_last_collection_date() -> Optional[date]:
    """
    로그 파일에서 마지막 수집 날짜 추출

    collect_result_*.json 파일명에서 날짜를 추출하여 가장 최근 날짜를 반환.

    Returns:
        가장 최근 수집 날짜 (파일이 없으면 None)
    """
    if not LOGS_DIR.exists():
        logger.debug("로그 디렉토리가 존재하지 않음")
        return None

    # 패턴: collect_result_YYYY-MM-DD.json
    pattern = re.compile(r'collect_result_(\d{4}-\d{2}-\d{2})\.json')

    dates = []
    for file in LOGS_DIR.glob('collect_result_*.json'):
        match = pattern.match(file.name)
        if match:
            try:
                date_str = match.group(1)
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                dates.append(file_date)
            except ValueError:
                logger.warning(f"파일명에서 날짜 파싱 실패: {file.name}")
                continue

    if dates:
        last_date = max(dates)
        logger.info(f"마지막 수집 날짜: {last_date}")
        return last_date

    logger.debug("로그 파일에서 수집 날짜를 찾을 수 없음 (첫 실행)")
    return None


def get_collection_date_range(default_days_back: int = 7) -> tuple[date, date]:
    """
    수집할 날짜 범위 계산

    마지막 수집 날짜를 기준으로 다음날부터 오늘까지 범위를 계산.

    Args:
        default_days_back: 수집 이력이 없을 때 과거 며칠부터 수집할지

    Returns:
        (start_date, end_date) 튜플
    """
    today = date.today()
    last_date = get_last_collection_date()

    if last_date:
        start_date = last_date + timedelta(days=1)
        logger.info(f"마지막 수집 날짜: {last_date}, 다음 수집 시작: {start_date}")
    else:
        start_date = today - timedelta(days=default_days_back)
        logger.info(f"첫 실행, {default_days_back}일 전부터 수집: {start_date}")

    if start_date > today:
        logger.info("수집할 데이터 없음 (이미 최신)")
        return (today, today - timedelta(days=1))

    logger.info(f"수집 범위: {start_date} ~ {today}")
    return (start_date, today)
