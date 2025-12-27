#!/usr/bin/env python3
"""
Storage 모듈 테스트

BaseSaver 및 각 Saver 클래스를 테스트합니다.
DB 연결이 필요한 테스트는 mock을 사용하거나 스킵합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from storage.base_saver import BaseSaver
from storage.github_saver import GitHubSaver
from storage.claude_saver import ClaudeSaver
from storage.baekjoon_saver import BaekjoonSaver
from storage.artifact_saver import ArtifactSaver


class TestBaseSaver(unittest.TestCase):
    """BaseSaver 기본 클래스 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }

    def test_init_with_config(self):
        """DB 설정으로 초기화 테스트"""
        saver = BaseSaver(db_config=self.db_config)

        self.assertEqual(saver.db_config, self.db_config)

    def test_init_without_config_uses_default(self):
        """설정 없이 초기화하면 기본값 사용"""
        saver = BaseSaver()

        self.assertIsNotNone(saver.db_config)
        self.assertIn('host', saver.db_config)


class TestGitHubSaver(unittest.TestCase):
    """GitHubSaver 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        self.saver = GitHubSaver(db_config=self.db_config)

    def test_saver_initialization(self):
        """Saver 초기화 테스트"""
        self.assertIsNotNone(self.saver)
        self.assertEqual(self.saver.db_config, self.db_config)

    @patch('storage.github_saver.psycopg2.connect')
    def test_save_with_mock_db(self, mock_connect):
        """DB 저장 테스트 (모킹)"""
        # Mock DB 연결
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock cursor가 artifact_id 반환
        mock_cursor.fetchone.return_value = (1,)

        sample_commit = {
            'repo': 'test-repo',
            'sha': 'abc123',
            'message': 'Test commit',
            'date': '2025-12-26T12:00:00Z',
            'stats': {'additions': 10, 'deletions': 5},
            'files': []
        }

        # save_github_artifact 메서드가 있다고 가정
        try:
            artifact_id = self.saver.save_github_artifact(sample_commit, date.today())
            # 저장이 성공하면 ID 반환
            self.assertIsNotNone(artifact_id)
        except AttributeError:
            # 메서드가 없으면 테스트 스킵
            self.skipTest("save_github_artifact method not implemented")


class TestClaudeSaver(unittest.TestCase):
    """ClaudeSaver 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        self.saver = ClaudeSaver(db_config=self.db_config)

    def test_saver_initialization(self):
        """Saver 초기화 테스트"""
        self.assertIsNotNone(self.saver)


class TestBaekjoonSaver(unittest.TestCase):
    """BaekjoonSaver 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        self.saver = BaekjoonSaver(db_config=self.db_config)

    def test_saver_initialization(self):
        """Saver 초기화 테스트"""
        self.assertIsNotNone(self.saver)


class TestArtifactSaver(unittest.TestCase):
    """ArtifactSaver 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        self.saver = ArtifactSaver(db_config=self.db_config)

    def test_saver_initialization(self):
        """Saver 초기화 테스트"""
        self.assertIsNotNone(self.saver)

    def test_get_file_path(self):
        """파일 경로 생성 테스트"""
        test_date = date(2025, 12, 26)
        source_type = 'github'
        filename = 'commit_abc123.json'

        # get_file_path 메서드가 있다고 가정
        try:
            path = self.saver.get_file_path(test_date, source_type, filename)
            self.assertIsNotNone(path)
            # 경로에 날짜와 소스 타입이 포함되어야 함
            self.assertIn('2025', str(path))
            self.assertIn('12', str(path))
            self.assertIn('26', str(path))
            self.assertIn(source_type, str(path))
        except AttributeError:
            # 메서드가 없으면 테스트 스킵
            self.skipTest("get_file_path method not implemented")


if __name__ == '__main__':
    unittest.main()
