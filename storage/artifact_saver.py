#!/usr/bin/env python3
"""
Learning Artifact Saver

학습 아티팩트를 파일 시스템 + PostgreSQL에 저장합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import psycopg2
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import logging

from config.settings import ARTIFACTS_DIR, get_log_file
from storage.base_saver import BaseSaver

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('artifact_saver')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ArtifactSaver(BaseSaver):
    """학습 아티팩트 저장 (파일 + DB)"""

    def __init__(self, db_config: Optional[Dict] = None):
        """
        Args:
            db_config: PostgreSQL 연결 정보
                {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'my_blog',
                    'user': 'postgres',
                    'password': 'postgres'
                }
        """
        super().__init__(db_config)
        logger.info(f"ArtifactSaver 초기화: {self.artifacts_dir}")

    def _get_db_connection(self):
        """PostgreSQL 연결"""
        return psycopg2.connect(**self.db_config)

    def _ensure_directory(self, artifact_date: date, source_type: str) -> Path:
        """날짜/소스별 디렉토리 생성"""
        date_path = self.artifacts_dir / str(artifact_date.year) / f"{artifact_date.month:02d}" / f"{artifact_date.day:02d}" / source_type
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    def save_to_file(self, data: Dict, artifact_date: date, source_type: str, filename: str) -> str:
        """
        파일 시스템에 저장

        Args:
            data: 저장할 데이터 (dict)
            artifact_date: 학습 날짜
            source_type: 소스 타입 (github, claude, baekjoon)
            filename: 파일명

        Returns:
            상대 경로 (learning_artifacts/2025/12/26/github/commit_abc.json)
        """
        dir_path = self._ensure_directory(artifact_date, source_type)
        file_path = dir_path / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # 상대 경로 반환
        relative_path = file_path.relative_to(PROJECT_ROOT)
        logger.info(f"파일 저장: {relative_path}")
        return str(relative_path)

    def save_artifact(
        self,
        artifact_date: date,
        source_type: str,
        title: str,
        tags: List[str],
        storage_path: str,
        summary: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        learning_artifacts 테이블에 저장

        Returns:
            artifact_id (삽입된 레코드의 id)
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO learning.learning_artifacts
                    (artifact_date, source_type, title, summary, tags, storage_path, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    artifact_date,
                    source_type,
                    title,
                    summary,
                    tags,
                    storage_path,
                    json.dumps(metadata or {})
                ))
                artifact_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] learning_artifacts 저장: id={artifact_id}, {title}")
                return artifact_id
        finally:
            conn.close()

    def save_github_commit(self, artifact_id: int, commit_data: Dict) -> int:
        """GitHub 커밋 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO learning.github_commits
                    (artifact_id, repo, repo_owner, sha, message, commit_date, url,
                     additions, deletions, files_changed, files, diff_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    artifact_id,
                    commit_data.get('repo'),
                    commit_data.get('repo_owner', commit_data.get('repo')),  # fallback
                    commit_data.get('sha'),
                    commit_data.get('message'),
                    commit_data.get('date'),
                    commit_data.get('url'),
                    commit_data.get('stats', {}).get('additions', 0),
                    commit_data.get('stats', {}).get('deletions', 0),
                    len(commit_data.get('files', [])),
                    json.dumps(commit_data.get('files', [])),
                    commit_data.get('diff_path')
                ))
                commit_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] github_commits 저장: id={commit_id}, sha={commit_data.get('sha')[:8]}")
                return commit_id
        finally:
            conn.close()

    def save_claude_conversation(self, artifact_id: int, conversation_data: Dict) -> int:
        """Claude 대화 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO learning.claude_conversations
                    (artifact_id, uuid, name, summary, user_messages, assistant_messages,
                     has_code, duration_minutes, conversation_path, code_languages, code_blocks_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    artifact_id,
                    conversation_data.get('uuid'),
                    conversation_data.get('name'),
                    conversation_data.get('summary'),
                    conversation_data.get('user_messages', 0),
                    conversation_data.get('assistant_messages', 0),
                    conversation_data.get('has_code', False),
                    conversation_data.get('duration_minutes'),
                    conversation_data.get('conversation_path'),
                    conversation_data.get('code_languages', []),
                    conversation_data.get('code_blocks_count', 0)
                ))
                conv_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] claude_conversations 저장: id={conv_id}, uuid={conversation_data.get('uuid')}")
                return conv_id
        finally:
            conn.close()

    def save_baekjoon_solution(self, artifact_id: int, solution_data: Dict) -> int:
        """백준 풀이 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO learning.baekjoon_solutions
                    (artifact_id, problem_id, title, tier, tags, url,
                     submission_id, language, memory, time, code_path, code_lines, comment_lines)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    artifact_id,
                    solution_data.get('problem_id'),
                    solution_data.get('title'),
                    solution_data.get('tier'),
                    solution_data.get('tags', []),
                    solution_data.get('url'),
                    solution_data.get('submission', {}).get('submission_id'),
                    solution_data.get('submission', {}).get('language'),
                    solution_data.get('submission', {}).get('memory'),
                    solution_data.get('submission', {}).get('time'),
                    solution_data.get('code_path'),
                    solution_data.get('code_analysis', {}).get('code_lines'),
                    solution_data.get('code_analysis', {}).get('comment_lines')
                ))
                solution_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[DB] baekjoon_solutions 저장: id={solution_id}, problem={solution_data.get('problem_id')}")
                return solution_id
        finally:
            conn.close()

    def save_github_artifact(self, commit_data: Dict, artifact_date: date) -> int:
        """
        GitHub 커밋 전체 저장 (파일 + DB)

        Args:
            commit_data: export에서 받은 커밋 데이터
            artifact_date: 학습 날짜

        Returns:
            artifact_id
        """
        # 1. 파일로 저장
        filename = f"commit_{commit_data['sha'][:8]}.json"
        storage_path = self.save_to_file(commit_data, artifact_date, 'github', filename)

        # 2. learning_artifacts에 저장
        artifact_id = self.save_artifact(
            artifact_date=artifact_date,
            source_type='github',
            title=commit_data['message'].split('\n')[0][:500],  # 첫 줄만, 최대 500자
            tags=['github', commit_data['repo']],
            storage_path=storage_path,
            summary=commit_data.get('message'),
            metadata={
                'repo': commit_data['repo'],
                'sha': commit_data['sha'],
                'url': commit_data['url']
            }
        )

        # 3. github_commits에 저장
        self.save_github_commit(artifact_id, commit_data)

        return artifact_id


if __name__ == '__main__':
    # 테스트
    saver = ArtifactSaver()

    # 테스트 데이터
    test_commit = {
        'repo': 'test-repo',
        'sha': 'abc123def456',
        'message': 'Add test feature\n\nDetailed description here',
        'date': '2025-12-26T10:00:00Z',
        'url': 'https://github.com/user/test-repo/commit/abc123',
        'files': [
            {
                'filename': 'test.py',
                'status': 'added',
                'additions': 10,
                'deletions': 0,
                'changes': 10
            }
        ],
        'stats': {
            'additions': 10,
            'deletions': 0
        }
    }

    print("테스트 데이터 저장 중...")
    artifact_id = saver.save_github_artifact(test_commit, date.today())
    print(f"저장 완료! artifact_id: {artifact_id}")
