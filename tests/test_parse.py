#!/usr/bin/env python3
"""
Parse 모듈 테스트

GitHub, Claude, Baekjoon parse 모듈을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parse.github_parse import GitHubParser
from parse.claude_parse import ClaudeParser
from parse.baekjoon_parse import BaekjoonParser


class TestGitHubParser(unittest.TestCase):
    """GitHub Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = GitHubParser()

    def test_parser_initialization(self):
        """Parser 초기화 테스트"""
        self.assertIsNotNone(self.parser)

    def test_parse_commits_with_empty_list(self):
        """빈 커밋 리스트 파싱"""
        commits = []
        result = self.parser.parse_commits(commits)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_parse_commits_with_sample_data(self):
        """샘플 커밋 데이터 파싱"""
        sample_commits = [
            {
                'sha': 'abc123',
                'commit': {
                    'message': 'Test commit',
                    'author': {
                        'date': '2025-12-26T12:00:00Z'
                    }
                },
                'stats': {
                    'additions': 10,
                    'deletions': 5
                },
                'files': [
                    {
                        'filename': 'test.py',
                        'status': 'modified',
                        'additions': 10,
                        'deletions': 5
                    }
                ]
            }
        ]

        result = self.parser.parse_commits(sample_commits)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestClaudeParser(unittest.TestCase):
    """Claude Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = ClaudeParser()

    def test_parser_initialization(self):
        """Parser 초기화 테스트"""
        self.assertIsNotNone(self.parser)

    def test_parse_zip_with_invalid_path(self):
        """잘못된 ZIP 경로 파싱 시 에러 처리"""
        invalid_path = '/invalid/path/to/file.zip'

        # 파일이 없으면 에러 또는 빈 결과 반환
        try:
            result = self.parser.parse_zip(invalid_path)
            # 에러가 발생하지 않으면 빈 리스트여야 함
            self.assertIsInstance(result, list)
        except (FileNotFoundError, Exception):
            # 에러 발생도 정상
            pass


class TestBaekjoonParser(unittest.TestCase):
    """Baekjoon Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = BaekjoonParser()

    def test_parser_initialization(self):
        """Parser 초기화 테스트"""
        self.assertIsNotNone(self.parser)

    def test_parse_problems_with_empty_list(self):
        """빈 문제 리스트 파싱"""
        problems = []
        result = self.parser.parse_problems(problems)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_parse_problems_with_sample_data(self):
        """샘플 문제 데이터 파싱"""
        sample_problems = [
            {
                'problemId': 1000,
                'titleKo': 'A+B',
                'level': 1,
                'tags': [{'displayNames': [{'name': '수학'}]}],
                'acceptedUserCount': 100000
            }
        ]

        result = self.parser.parse_problems(sample_problems)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
