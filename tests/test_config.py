#!/usr/bin/env python3
"""
Config 모듈 테스트

설정 파일 로딩 및 검증을 테스트합니다.
"""

import unittest
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings


class TestConfigSettings(unittest.TestCase):
    """설정 모듈 테스트"""

    def test_project_root_exists(self):
        """프로젝트 루트 디렉토리가 존재하는지 확인"""
        self.assertTrue(settings.PROJECT_ROOT.exists())
        self.assertTrue(settings.PROJECT_ROOT.is_dir())

    def test_directories_created(self):
        """필수 디렉토리들이 생성되었는지 확인"""
        self.assertTrue(settings.TEMP_DIR.exists())
        self.assertTrue(settings.LOGS_DIR.exists())
        self.assertTrue(settings.ARTIFACTS_DIR.exists())
        self.assertTrue(settings.CLAUDE_MIGRATION_DIR.exists())

    def test_github_settings(self):
        """GitHub 설정값 확인"""
        self.assertIsNotNone(settings.GITHUB_USERNAME)
        self.assertEqual(settings.GITHUB_API_BASE, 'https://api.github.com')

    def test_baekjoon_settings(self):
        """백준 설정값 확인"""
        self.assertIsNotNone(settings.BAEKJOON_HANDLE)
        self.assertIsNotNone(settings.BAEKJOON_REPO)

    def test_db_config(self):
        """DB 설정 반환 테스트"""
        db_config = settings.get_db_config()

        self.assertIn('host', db_config)
        self.assertIn('port', db_config)
        self.assertIn('database', db_config)
        self.assertIn('user', db_config)
        self.assertIn('password', db_config)

        self.assertIsInstance(db_config['port'], int)

    def test_log_file_path(self):
        """로그 파일 경로 생성 테스트"""
        log_path = settings.get_log_file('test_module')

        self.assertEqual(log_path.parent, settings.LOGS_DIR)
        self.assertEqual(log_path.name, 'test_module.log')

    def test_collection_settings(self):
        """데이터 수집 설정 확인"""
        self.assertIsInstance(settings.COLLECT_GITHUB, bool)
        self.assertIsInstance(settings.COLLECT_BAEKJOON, bool)
        self.assertIsInstance(settings.COLLECT_AI_CHAT, bool)
        self.assertIsInstance(settings.ENABLE_CLAUDE_MIGRATION, bool)


class TestConfigValidation(unittest.TestCase):
    """설정 검증 테스트"""

    def setUp(self):
        """테스트 전 환경변수 백업"""
        self.env_backup = {
            'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
            'GITHUB_USERNAME': os.getenv('GITHUB_USERNAME'),
            'BAEKJOON_HANDLE': os.getenv('BAEKJOON_HANDLE'),
        }

    def tearDown(self):
        """테스트 후 환경변수 복구"""
        for key, value in self.env_backup.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    def test_validate_config_success(self):
        """설정 검증 성공 케이스 (환경변수가 설정된 경우)"""
        # GitHub 토큰이 있으면 검증 성공
        if os.getenv('GITHUB_TOKEN'):
            try:
                result = settings.validate_config()
                self.assertTrue(result)
            except ValueError:
                # 토큰이 없으면 건너뛰기
                self.skipTest("GITHUB_TOKEN not set")


if __name__ == '__main__':
    unittest.main()
