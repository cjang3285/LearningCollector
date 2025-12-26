#!/usr/bin/env python3
"""
Baekjoon Saver - 백준 문제 풀이 DB 저장
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
        logging.FileHandler(get_log_file('baekjoon_saver')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaekjoonSaver(BaseSaver):
    """백준 문제 풀이 DB 저장"""

    def save_solution(self, artifact_id: int, solution_data: Dict) -> int:
        """baekjoon_solutions 테이블에 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                submission = solution_data.get("submission", {})
                code_analysis = solution_data.get("code_analysis", {})

                cur.execute(
                    """
                    INSERT INTO learning.baekjoon_solutions
                    (artifact_id, problem_id, title, tier, tags, url,
                     submission_id, language, memory, time, code_path, code_lines, comment_lines)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        artifact_id,
                        solution_data.get("problem_id"),
                        solution_data.get("title"),
                        solution_data.get("tier"),
                        solution_data.get("tags", []),
                        solution_data.get("url"),
                        submission.get("submission_id"),
                        submission.get("language"),
                        submission.get("memory"),
                        submission.get("time"),
                        solution_data.get("code_path"),
                        code_analysis.get("code_lines"),
                        code_analysis.get("comment_lines"),
                    ),
                )
                solution_id = cur.fetchone()[0]
                conn.commit()
                logger.info(
                    f"[DB] baekjoon_solutions 저장: id={solution_id}, problem={solution_data.get('problem_id')}"
                )
                return solution_id
        finally:
            conn.close()

    def save_baekjoon_artifact(
        self, solution_data: Dict, artifact_date: date
    ) -> int:
        """백준 풀이 전체 저장 (파일 + DB)"""
        # 1. 코드 파일 저장
        problem_id = solution_data["problem_id"]
        code_filename = f"problem_{problem_id}.py"
        code_path = self._ensure_directory(artifact_date, "baekjoon") / code_filename

        submission = solution_data.get("submission", {})
        if submission.get("code"):
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(submission["code"])
            logger.info(f"코드 파일 저장: {code_path}")

        # 2. 메타데이터 JSON 저장
        json_filename = f"problem_{problem_id}_meta.json"
        storage_path = self.save_to_file(
            solution_data, artifact_date, "baekjoon", json_filename
        )

        # 3. learning_artifacts에 저장
        artifact_id = self.save_artifact(
            artifact_date=artifact_date,
            source_type="baekjoon",
            title=f"[{solution_data.get('tier')}] {solution_data.get('title', 'Untitled')}",
            tags=["baekjoon", solution_data.get("tier")] + solution_data.get("tags", []),
            storage_path=storage_path,
            summary=f"Problem {problem_id}",
            metadata={
                "problem_id": problem_id,
                "tier": solution_data.get("tier"),
                "language": submission.get("language"),
            },
        )

        # 4. baekjoon_solutions에 저장
        solution_data["code_path"] = str(code_path.relative_to(self.artifacts_dir.parent))
        self.save_solution(artifact_id, solution_data)

        return artifact_id

    def save_all(self, solutions: List[Dict], artifact_date: date) -> List[int]:
        """여러 풀이 일괄 저장"""
        artifact_ids = []
        for solution in solutions:
            try:
                artifact_id = self.save_baekjoon_artifact(solution, artifact_date)
                artifact_ids.append(artifact_id)
            except Exception as e:
                logger.error(
                    f"풀이 저장 실패 (problem={solution.get('problem_id', 'unknown')}): {e}"
                )
                continue

        logger.info(f"백준 풀이 {len(artifact_ids)}개 저장 완료")
        return artifact_ids
