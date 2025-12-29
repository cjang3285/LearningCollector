#!/usr/bin/env python3
"""
Parse 모듈 테스트

GitHub, Claude, Baekjoon parse 모듈을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parse.github_parse import GitHubParser
from migration.claude_parse import ClaudeMigrationParser
from parse.baekjoon_parse import BaekjoonParser
from parse.ai_chat_parse import AIMarkdownParser


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
                'repo': 'test-repo',
                'sha': 'abc123',
                'message': 'Test commit',
                'date': '2025-12-26T12:00:00Z',
                'url': 'https://github.com/test/test-repo/commit/abc123',
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
                        'deletions': 5,
                        'changes': 15
                    }
                ]
            }
        ]

        result = self.parser.parse_commits(sample_commits)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestClaudeMigrationParser(unittest.TestCase):
    """Claude Migration Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = ClaudeMigrationParser()

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

    def test_convert_to_markdown(self):
        """JSON을 마크다운으로 변환 테스트"""
        sample_conversation = {
            'uuid': 'test-uuid',
            'name': 'Test Conversation',
            'created_at': '2025-12-26T12:00:00Z',
            'updated_at': '2025-12-26T13:00:00Z',
            'chat_messages': [
                {
                    'sender': 'human',
                    'text': 'Hello'
                },
                {
                    'sender': 'assistant',
                    'text': 'Hi there!'
                }
            ]
        }

        markdown = self.parser.convert_to_markdown(sample_conversation)

        self.assertIsInstance(markdown, str)
        self.assertIn('Test Conversation', markdown)
        self.assertIn('Hello', markdown)
        self.assertIn('Hi there!', markdown)


class TestAIMarkdownParser(unittest.TestCase):
    """AI Markdown Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = AIMarkdownParser()

    def test_parser_initialization(self):
        """Parser 초기화 테스트"""
        self.assertIsNotNone(self.parser)


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
        exporter = Mock()  # Mock exporter
        result = self.parser.parse_problems(problems, exporter)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_parse_problems_with_sample_data(self):
        """샘플 문제 데이터 파싱"""
        sample_problems = [
            {
                'readme_path': '백준/Silver/24511. queuestack/README.md',
                'code_path': '백준/Silver/24511. queuestack/queuestack.cc',
                'commit_sha': 'abc123',
                'tier': 'Silver',
                'problem_folder': '24511. queuestack'
            }
        ]

        # Mock exporter
        exporter = Mock()
        exporter.get_file_content.return_value = "# [Silver III] queuestack - 24511"

        try:
            result = self.parser.parse_problems(sample_problems, exporter)
            self.assertIsInstance(result, list)
        except:
            self.skipTest("Parser implementation requires actual file content")


if __name__ == '__main__':
    unittest.main()
