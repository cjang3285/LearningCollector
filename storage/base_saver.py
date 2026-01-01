#!/usr/bin/env python3
"""
Base Saver - DB 저장 기본 클래스
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from storage.db_client import get_connection
from datetime import date
from typing import Dict, Optional
import logging

from config.settings import get_log_file, get_db_config

logger = logging.getLogger(__name__)


class BaseSaver:
    """DB 저장 기본 클래스"""

    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or get_db_config()
        # PROJECT_ROOT 기반 경로 사용 (하드코딩 제거)
        from config.settings import ARTIFACTS_DIR
        self.artifacts_dir = ARTIFACTS_DIR

    def _get_db_connection(self):
        """PostgreSQL 연결"""
        return get_connection(self.db_config)

    def _execute(self, query: str, params: tuple = (), fetchone: bool = False, commit: bool = False):
        """Execute a query against the DB and optionally fetch one row.

        This centralizes connection handling to reduce repetitive try/finally blocks.
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone() if fetchone else None
                if commit:
                    conn.commit()
                return result
        finally:
            conn.close()

    def _ensure_directory(self, artifact_date: date, source_type: str) -> Path:
        """날짜/소스별 디렉토리 생성"""
        date_path = (
            self.artifacts_dir
            / str(artifact_date.year)
            / f"{artifact_date.month:02d}"
            / f"{artifact_date.day:02d}"
            / source_type
        )
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    def save_to_file(
        self, data: Dict, artifact_date: date, source_type: str, filename: str
    ) -> str:
        """파일 시스템에 저장"""
        dir_path = self._ensure_directory(artifact_date, source_type)
        file_path = dir_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        relative_path = file_path.relative_to(self.artifacts_dir.parent)
        logger.info(f"파일 저장: {relative_path}")
        return str(relative_path)

    def save_artifact(
        self,
        artifact_date: date,
        source_type: str,
        title: str,
        tags: list,
        storage_path: str,
        summary: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        """learning_artifacts 테이블에 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learning.learning_artifacts
                    (artifact_date, source_type, title, summary, tags, storage_path, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        artifact_date,
                        source_type,
                        title,
                        summary,
                        tags,
                        storage_path,
                        json.dumps(metadata or {}),
                    ),
                )
                artifact_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] learning_artifacts 저장: id={artifact_id}")
                return artifact_id
        finally:
            conn.close()
