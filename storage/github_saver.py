#!/usr/bin/env python3
"""
GitHub Saver - GitHub 커밋 DB 저장
ISaver 인터페이스 구현 (SOLID - DIP)
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date
from typing import Dict, List, Optional
import logging

from storage.base_saver import BaseSaver
from interfaces import ISaver, SaveError
from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('github_saver'), __name__)


class GitHubSaver(BaseSaver, ISaver):
    """GitHub 커밋 DB 저장 (ISaver 구현)"""

    # ============================================
    # ISaver 인터페이스 구현
    # ============================================

    def save(self, data: Dict, artifact_date: date) -> Optional[int]:
        """
        단일 GitHub 커밋 저장 (ISaver 인터페이스)

        Args:
            data: GitHub 커밋 데이터
            artifact_date: 아티팩트 날짜

        Returns:
            artifact_id (성공 시), None (중복/실패 시)

        Raises:
            SaveError: 저장 실패 시
        """
        try:
            return self.save_github_artifact(data, artifact_date)
        except Exception as e:
            raise SaveError(f"GitHub 커밋 저장 실패: {e}") from e

    def save_all(self, data_list: List[Dict], artifact_date: date) -> List[int]:
        """
        여러 GitHub 커밋 일괄 저장 (ISaver 인터페이스)

        Args:
            data_list: GitHub 커밋 데이터 리스트
            artifact_date: 아티팩트 날짜

        Returns:
            성공한 artifact_id 리스트

        Raises:
            SaveError: 저장 실패 시
        """
        artifact_ids = []
        skipped_count = 0
        error_count = 0

        for commit in data_list:
            try:
                artifact_id = self.save(commit, artifact_date)
                if artifact_id:
                    artifact_ids.append(artifact_id)
                else:
                    skipped_count += 1
            except SaveError as e:
                error_count += 1
                logger.error(f"커밋 저장 실패 (sha={commit.get('sha', 'unknown')[:8]}): {e}")
                continue

        logger.info(
            f"[GitHub] 커밋 저장 완료: 성공 {len(artifact_ids)}개, "
            f"중복 스킵 {skipped_count}개, 오류 {error_count}개"
        )
        return artifact_ids

    def check_duplicate(self, data: Dict) -> bool:
        """
        중복 커밋 확인 (ISaver 인터페이스)

        Args:
            data: GitHub 커밋 데이터

        Returns:
            중복이면 True, 아니면 False
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM learning.github_commits
                    WHERE sha = %s
                    LIMIT 1
                    """,
                    (data.get('sha'),)
                )
                if cur.fetchone():
                    logger.info(f"[중복] SHA로 감지: {data.get('sha')[:8]}")
                    return True
                return False
        finally:
            conn.close()

    # ============================================
    # 내부 구현 메서드 (GitHub 전용)
    # ============================================

    def save_commit(self, artifact_id: int, commit_data: Dict) -> int:
        """github_commits 테이블에 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learning.github_commits
                    (artifact_id, repo, repo_owner, sha, message, commit_date, url,
                     additions, deletions, files_changed, files, diff_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sha) DO NOTHING
                    RETURNING id
                """,
                    (
                        artifact_id,
                        commit_data.get("repo"),
                        commit_data.get("repo_owner", commit_data.get("repo")),
                        commit_data.get("sha"),
                        commit_data.get("message"),
                        commit_data.get("date"),
                        commit_data.get("url"),
                        commit_data.get("stats", {}).get("additions", 0),
                        commit_data.get("stats", {}).get("deletions", 0),
                        len(commit_data.get("files", [])),
                        json.dumps(commit_data.get("files", [])),
                        commit_data.get("diff_path"),
                    ),
                )
                result = cur.fetchone()
                conn.commit()

                if result:
                    commit_id = result[0]
                    logger.info(
                        f"[DB] github_commits 저장: id={commit_id}, sha={commit_data.get('sha')[:8]}"
                    )
                    return commit_id
                else:
                    logger.info(f"[DB] 중복 커밋 스킵: sha={commit_data.get('sha')[:8]}")
                    return None
        finally:
            conn.close()

    def save_github_artifact(
        self, commit_data: Dict, artifact_date: date
    ) -> int:
        """GitHub 커밋 전체 저장 (파일 + DB)"""
        # 1. 파일로 저장
        filename = f"commit_{commit_data['sha'][:8]}.json"
        storage_path = self.save_to_file(
            commit_data, artifact_date, "github", filename
        )

        # 2. learning_artifacts에 저장
        artifact_id = self.save_artifact(
            artifact_date=artifact_date,
            source_type="github",
            title=commit_data["message"].split("\n")[0][:500],
            tags=["github", commit_data["repo"]],
            storage_path=storage_path,
            summary=commit_data.get("message"),
            metadata={
                "repo": commit_data["repo"],
                "sha": commit_data["sha"],
                "url": commit_data["url"],
            },
        )

        # 3. github_commits에 저장
        self.save_commit(artifact_id, commit_data)

        return artifact_id
