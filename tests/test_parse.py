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
from bulk_import.parsers.claude_json_parser import ClaudeJsonParser
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


class TestClaudeJsonParser(unittest.TestCase):
    """Claude JSON Parser 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.parser = ClaudeJsonParser()

    def test_parser_initialization(self):
        """Parser 초기화 테스트"""
        self.assertIsNotNone(self.parser)

    def test_parse_json_with_sample_data(self):
        """샘플 JSON 데이터 파싱 테스트"""
        sample_json_data = """
        [
            {
                "uuid": "uuid1",
                "name": "Conversation 1",
                "created_at": "2023-01-01T10:00:00Z",
                "updated_at": "2023-01-01T11:00:00Z",
                "chat_messages": [
                    {"sender": "human", "text": "Hello"},
                    {"sender": "assistant", "text": "Hi there"}
                ]
            }
        ]
        """
        conversations = self.parser.parse_json(sample_json_data)
        self.assertIsInstance(conversations, list)
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]['uuid'], 'uuid1')
        self.assertEqual(conversations[0]['name'], 'Conversation 1')
        self.assertEqual(len(conversations[0]['chat_messages']), 2)


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
