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
import psycopg2
from datetime import date
from typing import Dict, Optional
import logging

from config.settings import get_log_file, get_db_config

logger = logging.getLogger(__name__)


class BaseSaver:
    """DB 저장 기본 클래스"""

    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or get_db_config()
        # 라즈베리파이 경로로 변경
        if os.path.exists('/home/jcw/learning-etl'):
            self.artifacts_dir = Path('/home/jcw/learning-etl/learning_artifacts')
        else:
            # 로컬 개발 환경
            from config.settings import ARTIFACTS_DIR
            self.artifacts_dir = ARTIFACTS_DIR

    def _get_db_connection(self):
        """PostgreSQL 연결"""
        return psycopg2.connect(**self.db_config)

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
