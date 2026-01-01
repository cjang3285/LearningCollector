#!/usr/bin/env python3
"""
백준 파서 - 백준허브 연동 레포 README.md 파싱

백준허브가 자동 생성한 README.md에서 문제 정보를 추출합니다.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from parse.base_parser import BaseParser

from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('baekjoon_parse')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class BaekjoonProblemData:
    """파싱된 백준 문제 데이터"""
    problem_id: int
    title: str
    tier: str  # "Silver III", "Bronze V" 등
    memory: str  # "3336 KB"
    time: str  # "36 ms"
    tags: List[str]  # ["자료 구조", "스택", "덱", "큐"]
    submitted_at: Optional[str]  # "2025년 12월 29일 11:05:54"
    description: str  # 문제 설명 전체
    code: Optional[str]  # 제출 코드
    code_language: Optional[str]  # "cpp", "python" 등
    commit_sha: str
    commit_message: str

    def to_dict(self):
        """
        Saver가 바로 사용할 수 있는 nested 구조로 변환
        Parser 책임: 데이터 변환/정규화
        """
        return {
            'problem_id': self.problem_id,
            'title': self.title,
            'tier': self.tier,
            'tags': self.tags,
            'url': f"https://www.acmicpc.net/problem/{self.problem_id}",
            'submission': {
                'submission_id': None,  # 백준허브는 submission_id 제공 안 함
                'language': self.code_language,
                'memory': self.memory,
                'time': self.time,
                'code': self.code
            },
            'code_analysis': {
                'code_lines': None,  # TODO: 코드 분석 기능 추가 시
                'comment_lines': None
            },
            # 추가 메타데이터
            'description': self.description,
            'submitted_at': self.submitted_at,
            'commit_sha': self.commit_sha,
            'commit_message': self.commit_message
        }


class BaekjoonParser(BaseParser):
    """백준 README.md 파서"""

    def parse(self, problem: Dict) -> Dict:
        """
        Parse a single exported problem dict into the saver-ready dict.

        Args:
            problem: dict returned by exporter describing file paths and commit info

        Returns:
            dict: parsed problem ready for saver
        """
        if not hasattr(self, 'exporter') or self.exporter is None:
            raise ValueError("BaekjoonParser.parse requires `self.exporter` to be set")

        # README 읽기
        readme_content = self.exporter.get_file_content(
            problem['readme_path'],
            ref=problem['commit_sha']
        )

        if not readme_content:
            logger.warning(f"README를 읽을 수 없음: {problem['readme_path']}")
            return None

        # 코드 읽기 (있는 경우)
        code_content = None
        if problem.get('code_path'):
            code_content = self.exporter.get_file_content(
                problem['code_path'],
                ref=problem['commit_sha']
            )

        parsed = self.parse_problem(
            readme_content=readme_content,
            code_content=code_content,
            code_path=problem.get('code_path'),
            commit_sha=problem.get('commit_sha'),
            commit_message=problem.get('commit_message')
        )

        return parsed.to_dict()

    def parse_readme(self, content: str) -> Dict:
        """
        README.md 내용을 파싱하여 문제 정보 추출

        Args:
            content: README.md 파일 내용

        Returns:
            파싱된 정보 딕셔너리
        """
        result = {
            'problem_id': None,
            'title': None,
            'tier': None,
            'memory': None,
            'time': None,
            'tags': [],
            'submitted_at': None,
            'description': None
        }

        # 1. 제목 및 문제 번호 추출
        # 형식: # [Silver III] queuestack - 24511
        title_match = re.search(r'#\s+\[(.+?)\]\s+(.+?)\s+-\s+(\d+)', content)
        if title_match:
            result['tier'] = title_match.group(1).strip()  # "Silver III"
            result['title'] = title_match.group(2).strip()  # "queuestack"
            result['problem_id'] = int(title_match.group(3))  # 24511

        # 2. 성능 요약 추출
        # 형식: 메모리: 3336 KB, 시간: 36 ms
        perf_match = re.search(r'메모리:\s*(\d+\s*KB),\s*시간:\s*(\d+\s*ms)', content)
        if perf_match:
            result['memory'] = perf_match.group(1).strip()  # "3336 KB"
            result['time'] = perf_match.group(2).strip()  # "36 ms"

        # 3. 분류 태그 추출
        # 형식: **분류**\n자료 구조, 스택, 덱, 큐
        tags_match = re.search(r'\*\*분류\*\*\s*\n(.+)', content)
        if tags_match:
            tags_line = tags_match.group(1).strip()
            result['tags'] = [tag.strip() for tag in tags_line.split(',')]

        # 4. 제출 일자 추출
        # 형식: **제출 일자**\n2025년 12월 29일 11:05:54
        date_match = re.search(r'\*\*제출 일자\*\*\s*\n(.+)', content)
        if date_match:
            result['submitted_at'] = date_match.group(1).strip()

        # 5. 문제 설명 추출
        # **문제 설명** 이후부터 코드 블록 또는 파일 끝까지
        desc_match = re.search(r'\*\*문제 설명\*\*\s*\n(.+?)(?=```|\Z)', content, re.DOTALL)
        if desc_match:
            result['description'] = desc_match.group(1).strip()

        return result

    def detect_language(self, file_path: str) -> str:
        """
        파일 확장자로 언어 감지

        Args:
            file_path: 코드 파일 경로

        Returns:
            언어 코드 ("cpp", "python", "java" 등)
        """
        ext_map = {
            '.cc': 'cpp',
            '.cpp': 'cpp',
            '.c': 'c',
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.kt': 'kotlin',
            '.swift': 'swift'
        }

        ext = Path(file_path).suffix
        return ext_map.get(ext, 'unknown')

    def parse_problem(
        self,
        readme_content: str,
        code_content: Optional[str],
        code_path: Optional[str],
        commit_sha: str,
        commit_message: str
    ) -> BaekjoonProblemData:
        """
        README와 코드를 합쳐서 완전한 문제 데이터 생성

        Args:
            readme_content: README.md 내용
            code_content: 코드 파일 내용
            code_path: 코드 파일 경로
            commit_sha: 커밋 SHA
            commit_message: 커밋 메시지

        Returns:
            파싱된 문제 데이터
        """
        # README 파싱
        readme_data = self.parse_readme(readme_content)

        # 언어 감지
        code_language = None
        if code_path:
            code_language = self.detect_language(code_path)

        # 데이터 구조화
        return BaekjoonProblemData(
            problem_id=readme_data['problem_id'],
            title=readme_data['title'],
            tier=readme_data['tier'],
            memory=readme_data['memory'],
            time=readme_data['time'],
            tags=readme_data['tags'],
            submitted_at=readme_data['submitted_at'],
            description=readme_data['description'],
            code=code_content,
            code_language=code_language,
            commit_sha=commit_sha,
            commit_message=commit_message
        )

    def parse_problems(
        self,
        problems: List[Dict],
        exporter  # BaekjoonExporter 인스턴스
    ) -> List[Dict]:
        """
        Export에서 수집한 문제 리스트를 파싱 (IParser 인터페이스 준수)

        Args:
            problems: Export에서 반환한 문제 리스트
            exporter: BaekjoonExporter 인스턴스 (파일 읽기용)

        Returns:
            파싱/검증된 문제 데이터 (Dict 리스트)
        """
        parsed_problems = []

        # exporter assigned to instance so parse() can use it
        self.exporter = exporter

        for problem in problems:
            try:
                parsed = self.parse(problem)
                if parsed:
                    parsed_problems.append(parsed)
                    logger.info(f"[OK] 파싱 완료: {parsed.get('problem_id')} - {parsed.get('title')}")
            except Exception as e:
                logger.error(f"파싱 실패 ({problem.get('problem_folder', 'unknown')}): {e}")
                continue

        return parsed_problems


if __name__ == '__main__':
    # 테스트용 README 내용
    test_readme = """# [Silver III] queuestack - 24511

**성능 요약**
메모리: 3336 KB, 시간: 36 ms

**분류**
자료 구조, 스택, 덱, 큐

**제출 일자**
2025년 12월 29일 11:05:54

**문제 설명**

한가롭게 방학에 놀고 있던 도현이는 갑자기 재밌는 자료구조를 생각해냈다.
그 자료구조의 이름은 queuestack이다.
"""

    parser = BaekjoonParser()
    result = parser.parse_readme(test_readme)

    print("\n파싱 결과:")
    for key, value in result.items():
        print(f"  {key}: {value}")
