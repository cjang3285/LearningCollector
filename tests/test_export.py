#!/usr/bin/env python3
"""
Export 모듈 테스트

GitHub 및 Baekjoon export 모듈을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from export.github_export import GitHubExporter
from export.baekjoon_export import BaekjoonExporter


class TestGitHubExporter(unittest.TestCase):
    """GitHub Exporter 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        # 토큰 없이 초기화하면 에러 발생 예상
        pass

    def test_init_without_token_raises_error(self):
        """토큰 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            GitHubExporter(token=None, username='testuser')

    @patch('export.github_export.GITHUB_USERNAME', None)
    def test_init_without_username_raises_error(self):
        """유저네임 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            GitHubExporter(token='test_token', username=None)

    def test_init_with_credentials(self):
        """정상적인 초기화 테스트"""
        exporter = GitHubExporter(token='test_token', username='testuser')

        self.assertEqual(exporter.token, 'test_token')
        self.assertEqual(exporter.username, 'testuser')
        self.assertIn('Authorization', exporter.headers)

    @patch('export.github_export.requests.get')
    def test_export_today_with_mock(self, mock_get):
        """당일 커밋 수집 테스트 (모킹)"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        exporter = GitHubExporter(token='test_token', username='testuser')
        commits = exporter.export_today()

        # API 호출 확인
        self.assertTrue(mock_get.called)
        # 결과는 리스트여야 함
        self.assertIsInstance(commits, list)


class TestBaekjoonExporter(unittest.TestCase):
    """Baekjoon Exporter 테스트"""

    def test_init_without_credentials_raises_error(self):
        """GitHub 인증 정보 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            BaekjoonExporter(username=None, token=None)

    def test_init_with_credentials(self):
        """정상적인 초기화 테스트"""
        exporter = BaekjoonExporter(
            baekjoon_repo='Baekjoon_solutions',
            username='testuser',
            token='test_token'
        )

        self.assertEqual(exporter.baekjoon_repo, 'Baekjoon_solutions')
        self.assertEqual(exporter.username, 'testuser')
        self.assertEqual(exporter.token, 'test_token')

    @patch('export.baekjoon_export.requests.get')
    def test_get_commits_with_mock(self, mock_get):
        """커밋 조회 테스트 (모킹)"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        exporter = BaekjoonExporter(
            username='testuser',
            token='test_token'
        )

        from datetime import datetime, timezone
        since = datetime.now(timezone.utc)
        until = datetime.now(timezone.utc)
        commits = exporter.get_commits(since, until)

        # API 호출 확인
        self.assertTrue(mock_get.called)
        # 결과는 리스트여야 함
        self.assertIsInstance(commits, list)


if __name__ == '__main__':
    unittest.main()
