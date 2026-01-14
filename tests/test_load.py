#!/usr/bin/env python3
"""
Load 모듈 테스트

GitHub 및 Baekjoon load 모듈을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from load.github_load import GitHubLoader
from load.baekjoon_load import BaekjoonLoader


class TestGitHubLoader(unittest.TestCase):
    """GitHub Loader 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        pass

    @patch('load.github_load.GITHUB_TOKEN', None)
    def test_init_without_token_raises_error(self):
        """토큰 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            GitHubLoader(token=None, usernames=['testuser'])

    @patch('load.github_load.GITHUB_USERNAMES', [])
    def test_init_without_username_raises_error(self):
        """유저네임 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            GitHubLoader(token='test_token', usernames=[])

    def test_init_with_credentials(self):
        """정상적인 초기화 테스트"""
        loader = GitHubLoader(token='test_token', usernames=['testuser', 'claude'])

        self.assertEqual(loader.token, 'test_token')
        self.assertEqual(loader.username, 'testuser')
        self.assertEqual(loader.usernames, ['testuser', 'claude'])
        self.assertIn('Authorization', loader.headers)

    @patch('load.github_load.GitHubLoader.get_user_repos')
    @patch('load.github_load.GitHubLoader.get_commits_by_date')
    def test_load_with_mock(self, mock_get_commits_by_date, mock_get_user_repos):
        """당일 커밋 수집 테스트 (모킹)"""
        # Mock 응답 설정
        mock_get_user_repos.return_value = [{'name': 'testrepo', 'owner': {'login': 'testuser'}}]
        mock_get_commits_by_date.return_value = [{'sha': '123', 'commit': {'message': 'test commit', 'author': {'date': '2026-01-01T10:00:00Z'}}, 'html_url': 'http://example.com'}]

        loader = GitHubLoader(token='test_token', usernames=['testuser'])
        commits = loader.load()

        # API 호출 확인
        mock_get_user_repos.assert_called_once()
        mock_get_commits_by_date.assert_called_once()
        # 결과는 리스트여야 함
        self.assertIsInstance(commits, list)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]['sha'], '123')


class TestBaekjoonLoader(unittest.TestCase):
    """Baekjoon Loader 테스트"""

    @patch('load.baekjoon_load.GITHUB_TOKEN', None)
    @patch('load.baekjoon_load.GITHUB_USERNAME', None)
    def test_init_without_credentials_raises_error(self):
        """GitHub 인증 정보 없이 초기화하면 에러 발생"""
        with self.assertRaises(ValueError):
            BaekjoonLoader(username=None, token=None)

    def test_init_with_credentials(self):
        """정상적인 초기화 테스트"""
        loader = BaekjoonLoader(
            baekjoon_repo='Baekjoon_solutions',
            username='testuser',
            token='test_token'
        )

        self.assertEqual(loader.baekjoon_repo, 'Baekjoon_solutions')
        self.assertEqual(loader.username, 'testuser')
        self.assertEqual(loader.token, 'test_token')

    @patch('load.baekjoon_load.requests.get')
    def test_get_commits_with_mock(self, mock_get):
        """커밋 조회 테스트 (모킹)"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        loader = BaekjoonLoader(
            username='testuser',
            token='test_token'
        )

        from datetime import datetime, timezone
        since = datetime.now(timezone.utc)
        until = datetime.now(timezone.utc)
        commits = loader.get_commits(since, until)

        # API 호출 확인
        self.assertTrue(mock_get.called)
        # 결과는 리스트여야 함
        self.assertIsInstance(commits, list)


if __name__ == '__main__':
    unittest.main()
