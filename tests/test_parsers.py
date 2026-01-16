"""Parser 모듈 테스트"""

import pytest
from pathlib import Path
from datetime import datetime
from parse.ai_chat_parse import AIMarkdownParser
from parse.github_parse import GitHubParser
from parse.baekjoon_parse import BaekjoonParser


class TestAIMarkdownParser:
    """AI 채팅 마크다운 파서 테스트"""

    def test_detect_provider_claude(self):
        """Claude 제공자 감지"""
        parser = AIMarkdownParser()

        assert parser.detect_provider('claude_conversation_2024-01-15.md') == 'claude'
        assert parser.detect_provider('Claude_Export_20240115.md') == 'claude'

    def test_detect_provider_chatgpt(self):
        """ChatGPT 제공자 감지"""
        parser = AIMarkdownParser()

        assert parser.detect_provider('chatgpt_export.md') == 'chatgpt'
        assert parser.detect_provider('ChatGPT_20240115.md') == 'chatgpt'

    def test_detect_provider_gemini(self):
        """Gemini 제공자 감지"""
        parser = AIMarkdownParser()

        assert parser.detect_provider('gemini_conversation.md') == 'gemini'
        assert parser.detect_provider('Gemini_Export_20250115.md') == 'gemini'

    def test_parse_claude_markdown(self, claude_markdown):
        """Claude 마크다운 파싱"""
        parser = AIMarkdownParser()
        result = parser.parse(str(claude_markdown))

        assert result is not None
        assert isinstance(result, dict)
        assert result['provider'] == 'claude'
        assert result['exchange_count'] >= 2

    def test_parse_gemini_markdown(self, gemini_markdown):
        """Gemini 마크다운 파싱"""
        parser = AIMarkdownParser()
        result = parser.parse(str(gemini_markdown))

        assert result is not None
        assert isinstance(result, dict)
        assert result['provider'] == 'gemini'
        assert result['exchange_count'] >= 2


class TestGitHubParser:
    """GitHub 파서 테스트"""

    def test_parse_commit_with_repo(self):
        """커밋 파싱 (repo 포함)"""
        parser = GitHubParser()

        commit_data = {
            'sha': 'abc123def456',
            'repo': 'test-repo',
            'commit': {
                'author': {
                    'name': 'Test User',
                    'email': 'test@example.com',
                    'date': '2024-01-15T10:30:00Z'
                },
                'message': 'Test commit'
            },
            'stats': {
                'additions': 10,
                'deletions': 5,
                'total': 15
            },
            'files': []
        }

        result = parser.parse(commit_data)

        assert result is not None
        assert isinstance(result, dict)
        assert result['sha'] == 'abc123def456'
        assert result['repo'] == 'test-repo'


class TestBaekjoonParser:
    """Baekjoon 파서 테스트"""

    def test_detect_language_python(self):
        """Python 언어 감지"""
        parser = BaekjoonParser()

        assert parser.detect_language('1000.py') == 'python'

    def test_detect_language_cpp(self):
        """C++ 언어 감지"""
        parser = BaekjoonParser()

        assert parser.detect_language('1000.cpp') == 'cpp'

    def test_parse_baekjoon_file(self, baekjoon_files):
        """Baekjoon 파일 파싱"""
        parser = BaekjoonParser()
        file_path = baekjoon_files['1000']

        result = parser.parse(str(file_path))

        assert result is not None
        assert isinstance(result, dict)
        assert 'problem_number' in result
        assert 'language' in result
