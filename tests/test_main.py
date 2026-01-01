#!/usr/bin/env python3
"""
Main ETL Pipeline 테스트

LearningETL 메인 클래스 및 전체 파이프라인을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock, ANY

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import LearningETL


class TestLearningETL(unittest.TestCase):
    """LearningETL 메인 클래스 테스트"""

    @patch('main.CollectorFactory.create_all_collectors')
    def test_init_without_collectors(self, mock_create_all_collectors):
        """Collector 없이 초기화 테스트"""
        mock_create_all_collectors.return_value = {}
        etl = LearningETL()
        self.assertEqual(len(etl.collectors), 0)
        mock_create_all_collectors.assert_called_once_with(enabled_only=True)

    @patch('main.CollectorFactory.create_all_collectors')
    def test_init_with_all_collectors(self, mock_create_all_collectors):
        """모든 Collector와 함께 초기화 테스트"""
        mock_github_collector = Mock()
        mock_claude_migration_collector = Mock()
        mock_baekjoon_collector = Mock()
        mock_ai_chat_collector = Mock()

        mock_create_all_collectors.return_value = {
            'github': mock_github_collector,
            'claude_migration': mock_claude_migration_collector,
            'baekjoon': mock_baekjoon_collector,
            'ai_chat': mock_ai_chat_collector
        }

        etl = LearningETL()

        self.assertIn('github', etl.collectors)
        self.assertIn('claude_migration', etl.collectors)
        self.assertIn('baekjoon', etl.collectors)
        self.assertIn('ai_chat', etl.collectors)
        self.assertEqual(etl.collectors['github'], mock_github_collector)
        mock_create_all_collectors.assert_called_once_with(enabled_only=True)

    @patch('main.CollectorFactory.create_all_collectors')
    def test_run_without_collectors(self, mock_create_all_collectors):
        """Collector 없이 실행 테스트"""
        mock_create_all_collectors.return_value = {} # No collectors created

        etl = LearningETL()
        result = etl.run(
            target_date=date.today(),
            skip_github=True,
            skip_baekjoon=True,
            skip_ai_chat=True
        )

        self.assertIsInstance(result, dict)
        self.assertIn('date', result)
        self.assertIn('timestamp', result)
        self.assertIn('summary', result)

        self.assertIsNone(result['github'])
        self.assertIsNone(result['baekjoon'])
        self.assertIsNone(result['claude']) # Claude migration is only run with import_zip=True
        self.assertIsNone(result['ai_chat'])

        self.assertEqual(result['summary']['total_artifacts'], 0)
        self.assertTrue(result['summary']['success'])

    @patch('main.CollectorFactory.create_all_collectors')
    def test_run_with_github_only(self, mock_create_all_collectors):
        """GitHub만 활성화하고 실행 테스트"""
        mock_github_collector = Mock()
        mock_github_collector.collect.return_value = MagicMock(
            success=True,
            items_count=5,
            artifact_ids=['gh1', 'gh2'],
            metadata={'repo_count': 1}
        )
        mock_create_all_collectors.return_value = {
            'github': mock_github_collector
        }

        etl = LearningETL()
        result = etl.run(
            target_date=date.today(),
            skip_github=False,
            skip_baekjoon=True,
            skip_ai_chat=True
        )

        self.assertIsNotNone(result['github'])
        self.assertEqual(result['github']['commits_count'], 5)
        self.assertTrue(result['summary']['success'])
        mock_github_collector.collect.assert_called_once()
        self.assertIsNone(result['baekjoon'])
        self.assertIsNone(result['claude'])
        self.assertIsNone(result['ai_chat'])

    @patch('bulk_import.claude_collector.ClaudeMigrationCollector')
    @patch('main.CollectorFactory.create_all_collectors')
    def test_run_with_claude_zip(self, mock_create_all_collectors, mock_claude_migration_collector_class):
        """Claude ZIP 파일과 함께 실행 테스트"""
        mock_create_all_collectors.return_value = {} # No other collectors
        mock_claude_instance = Mock()
        mock_claude_instance.collect.return_value = {
            'success': True,
            'conversations_count': 3
        }
        mock_claude_migration_collector_class.return_value = mock_claude_instance

        etl = LearningETL()
        result = etl.run(
            target_date=date.today(),
            import_zip=True
        )

        self.assertIsNotNone(result['claude'])
        self.assertEqual(result['claude']['conversations_count'], 3)
        self.assertTrue(result['claude']['success'])
        mock_claude_migration_collector_class.assert_called_once()
        mock_claude_instance.collect.assert_called_once_with(
            zip_path=None,
            target_date=ANY, # date.today() will be passed, but could be dynamic
            all_dates=False
        )
        self.assertTrue(result['summary']['success'])

    @patch('main.CollectorFactory.create_all_collectors')
    def test_run_returns_summary(self, mock_create_all_collectors):
        """실행 결과에 요약 정보가 포함되는지 확인"""
        mock_github_collector = Mock()
        mock_github_collector.collect.return_value = MagicMock(
            success=True, items_count=10, artifact_ids=[], metadata={})
        mock_baekjoon_collector = Mock()
        mock_baekjoon_collector.collect.return_value = MagicMock(
            success=True, items_count=5, artifact_ids=[], metadata={})
        mock_ai_chat_collector = Mock()
        mock_ai_chat_collector.collect_from_downloads.return_value = {
            'success': True, 'conversations_count': 2, 'providers': {'mock': 2}}

        mock_create_all_collectors.return_value = {
            'github': mock_github_collector,
            'baekjoon': mock_baekjoon_collector,
            'ai_chat': mock_ai_chat_collector
        }

        etl = LearningETL()
        result = etl.run(
            target_date=date.today(),
            skip_github=False,
            skip_baekjoon=False,
            ai_chat_scan=True # Enable AI Chat scan
        )

        self.assertIn('summary', result)
        self.assertIsInstance(result['summary'], dict)
        self.assertIn('total_artifacts', result['summary'])
        self.assertEqual(result['summary']['total_artifacts'], 17) # 10 + 5 + 2
        self.assertTrue(result['summary']['success'])
        self.assertEqual(result['summary']['github_commits'], 10)
        self.assertEqual(result['summary']['baekjoon_solutions'], 5)
        self.assertEqual(result['summary']['ai_chat_conversations'], 2)


if __name__ == '__main__':
    unittest.main()
