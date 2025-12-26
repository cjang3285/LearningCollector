#!/usr/bin/env python3
"""
GitHub Saver - GitHub 커밋 DB 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date
from typing import Dict, List
import logging

from db_savers.base_saver import BaseSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('github_saver')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GitHubSaver(BaseSaver):
    """GitHub 커밋 DB 저장"""

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

    def save_all(self, commits: List[Dict], artifact_date: date) -> List[int]:
        """여러 커밋 일괄 저장"""
        artifact_ids = []
        for commit in commits:
            try:
                artifact_id = self.save_github_artifact(commit, artifact_date)
                artifact_ids.append(artifact_id)
            except Exception as e:
                logger.error(f"커밋 저장 실패 (sha={commit.get('sha', 'unknown')[:8]}): {e}")
                continue

        logger.info(f"GitHub 커밋 {len(artifact_ids)}개 저장 완료")
        return artifact_ids
