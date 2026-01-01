#!/usr/bin/env python3
"""
Repository shim — re-exports DB helper functions.
This file provides an indirection layer so callers can switch implementations
later without touching collectors.
"""
from typing import Optional
from datetime import date, timedelta

from . import db_utils


def get_last_collection_date(source_type: str) -> Optional[date]:
    return db_utils.get_last_collection_date(source_type)


def get_collection_date_range(source_type: str, default_days_back: int = 7) -> tuple[date, date]:
    return db_utils.get_collection_date_range(source_type, default_days_back=default_days_back)


def has_data_for_date(source_type: str, target_date: date) -> bool:
    return db_utils.has_data_for_date(source_type, target_date)
