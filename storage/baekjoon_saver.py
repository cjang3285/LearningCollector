#!/usr/bin/env python3
"""
Baekjoon Saver - 백준 문제 풀이 DB 저장
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
logger = setup_logging(get_log_file('baekjoon_saver'), __name__)


class BaekjoonSaver(BaseSaver, ISaver):
    """백준 문제 풀이 DB 저장 (ISaver 구현)"""

    # ============================================
    # ISaver 인터페이스 구현
    # ============================================

    def save(self, data: Dict, artifact_date: date) -> Optional[int]:
        """
        단일 백준 풀이 저장 (ISaver 인터페이스)

        Args:
            data: 백준 풀이 데이터 (Dict 또는 BaekjoonProblemData)
            artifact_date: 아티팩트 날짜

        Returns:
            artifact_id (성공 시), None (중복/실패 시)

        Raises:
            SaveError: 저장 실패 시
        """
        try:
            # BaekjoonProblemData 객체면 dict로 변환하고 구조 맞추기
            if hasattr(data, 'to_dict'):
                data = data.to_dict()
                # BaekjoonProblemData 구조 → save_baekjoon_artifact 구조 변환
                # code, code_language를 submission 객체로 래핑
                if 'code' in data and 'submission' not in data:
                    data['submission'] = {
                        'code': data.get('code'),
                        'language': data.get('code_language')
                    }

            return self.save_baekjoon_artifact(data, artifact_date)
        except Exception as e:
            raise SaveError(f"백준 풀이 저장 실패: {e}") from e

    def save_all(self, data_list: List[Dict], artifact_date: date) -> List[int]:
        """
        여러 백준 풀이 일괄 저장 (ISaver 인터페이스)

        Args:
            data_list: 백준 풀이 데이터 리스트
            artifact_date: 아티팩트 날짜

        Returns:
            성공한 artifact_id 리스트

        Raises:
            SaveError: 저장 실패 시
        """
        artifact_ids = []
        skipped_count = 0
        error_count = 0

        for solution in data_list:
            try:
                artifact_id = self.save(solution, artifact_date)
                if artifact_id:
                    artifact_ids.append(artifact_id)
                else:
                    skipped_count += 1
            except SaveError as e:
                error_count += 1
                # BaekjoonProblemData 객체 또는 dict 처리
                problem_id = getattr(solution, 'problem_id', None) or solution.get('problem_id', 'unknown')
                logger.error(
                    f"풀이 저장 실패 (problem={problem_id}): {e}"
                )
                continue

        logger.info(
            f"[Baekjoon] 풀이 저장 완료: 성공 {len(artifact_ids)}개, "
            f"중복 스킵 {skipped_count}개, 오류 {error_count}개"
        )
        return artifact_ids

    def check_duplicate(self, data: Dict) -> bool:
        """
        중복 풀이 확인 (ISaver 인터페이스)

        Args:
            data: 백준 풀이 데이터

        Returns:
            중복이면 True, 아니면 False
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                # problem_id와 submission_id로 중복 체크
                submission = data.get("submission", {})
                cur.execute(
                    """
                    SELECT id FROM learning.baekjoon_solutions
                    WHERE problem_id = %s AND submission_id = %s
                    LIMIT 1
                    """,
                    (data.get('problem_id'), submission.get('submission_id'))
                )
                if cur.fetchone():
                    logger.info(f"[중복] Problem ID로 감지: {data.get('problem_id')}")
                    return True
                return False
        finally:
            conn.close()

    # ============================================
    # 내부 구현 메서드 (Baekjoon 전용)
    # ============================================

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
