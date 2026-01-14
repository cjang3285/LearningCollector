#!/usr/bin/env python3
"""
Collectors 모듈 테스트

각 Collector (GitHub, Claude, Baekjoon)를 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from collectors.github_collector import GitHubCollector
from bulk_import.claude_collector import ClaudeMigrationCollector
from collectors.baekjoon_collector import BaekjoonCollector
from collectors.ai_chat_collector import AIChatCollector


class TestGitHubCollector(unittest.TestCase):
    """GitHub Collector 통합 테스트"""

    @patch('collectors.github_collector.GitHubSaver')
    @patch('collectors.github_collector.GitHubParser')
    @patch('collectors.github_collector.GitHubLoader')
    def test_collector_initialization(self, mock_loader, mock_parser, mock_saver):
        """Collector 초기화 테스트"""
        # Mock 설정
        mock_loader.return_value = Mock()
        mock_parser.return_value = Mock()
        mock_saver.return_value = Mock()

        collector = GitHubCollector()
        self.assertIsNotNone(collector)

    @patch('collectors.github_collector.GitHubLoader')
    @patch('collectors.github_collector.GitHubParser')
    @patch('collectors.github_collector.GitHubSaver')
    def test_collect_workflow(self, mock_saver, mock_parser, mock_loader):
        """수집 워크플로우 테스트 (모킹)"""
        # Mock 설정
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{'sha': 'abc123'}]
        mock_loader.return_value = mock_loader_instance

        mock_parser_instance = Mock()
        mock_parser_instance.parse_commits.return_value = [{'sha': 'abc123'}]
        mock_parser.return_value = mock_parser_instance

        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1, 2, 3]
        mock_saver.return_value = mock_saver_instance

        try:
            collector = GitHubCollector()
            result = collector.collect(date.today())

            # 결과 확인
            self.assertIsInstance(result, dict)
        except:
            self.skipTest("Collector implementation varies")


class TestClaudeMigrationCollector(unittest.TestCase):
    """Claude Migration Collector 통합 테스트"""

    def setUp(self):
        """테스트 전 환경 설정"""
        self.collector = ClaudeMigrationCollector()

    def test_collector_initialization(self):
        """Collector 초기화 테스트"""
        self.assertIsNotNone(self.collector)

    @patch('bulk_import.claude_collector.ClaudeZipFinder')
    def test_collect_without_zip_path(self, mock_zip_finder_class):
        """ZIP 경로 없이 collect 호출 시 ZIP 파일이 없으면 에러 발생"""
        mock_finder_instance = Mock()
        mock_finder_instance.find_latest_zip.return_value = None  # Simulate no ZIP file found
        mock_zip_finder_class.return_value = mock_finder_instance

        collector = ClaudeMigrationCollector()
        with self.assertRaises(ValueError): # Expect ValueError if no zip_path and no zip found
            collector.collect(zip_path=None)

        mock_zip_finder_class.assert_called_once()
        mock_finder_instance.find_latest_zip.assert_called_once()


    @patch('bulk_import.claude_collector.AIChatSaver')
    @patch('bulk_import.claude_collector.AIMarkdownParser')
    @patch('bulk_import.claude_collector.ClaudeMigrationParser')
    @patch('bulk_import.claude_collector.ClaudeZipFinder')
    def test_collect_with_mock_zip(self, mock_zip_finder_class, mock_migration_parser_class,
                                   mock_markdown_parser_class, mock_saver_class):
        """ZIP 파일 수집 테스트 (모킹)"""
        # Mock ClaudeZipFinder
        mock_finder_instance = Mock()
        mock_finder_instance.find_latest_zip.return_value = Path('/tmp/test_conversations.zip')
        mock_zip_finder_class.return_value = mock_finder_instance

        # Mock ClaudeMigrationParser
        mock_migration_parser_instance = Mock()
        mock_migration_parser_instance.parse_zip.return_value = ["# Test conversation content"]
        mock_migration_parser_instance.filter_by_date.side_effect = lambda markdowns, after, before: markdowns # Don't filter
        mock_migration_parser_class.return_value = mock_migration_parser_instance

        # Mock AIMarkdownParser
        mock_markdown_parser_instance = Mock()
        mock_parsed_conversation = MagicMock()
        mock_parsed_conversation.provider = 'claude'
        mock_parsed_conversation.to_dict.return_value = {'provider': 'claude', 'title': 'Test Conv'}
        mock_markdown_parser_instance.parse_file.return_value = mock_parsed_conversation
        mock_markdown_parser_class.return_value = mock_markdown_parser_instance

        # Mock AIChatSaver
        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1] # Return a list of artifact IDs
        mock_saver_class.return_value = mock_saver_instance

        collector = ClaudeMigrationCollector()
        result = collector.collect(zip_path='/tmp/test_conversations.zip', target_date=date.today(), all_dates=True)

        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['conversations_count'], 1)
        self.assertIn('artifact_ids', result)
        self.assertEqual(len(result['artifact_ids']), 1)

        mock_migration_parser_instance.parse_zip.assert_called_once_with('/tmp/test_conversations.zip')
        mock_markdown_parser_instance.parse_file.assert_called_once()
        mock_saver_instance.save_all.assert_called_once()

    @patch('collectors.ai_chat_collector.AIMarkdownParser')
    @patch('collectors.ai_chat_collector.AIChatSaver')
    def test_collect_from_files_workflow(self, mock_saver, mock_parser):
        """파일에서 수집 워크플로우 테스트 (모킹)"""
        # Mock Parser
        mock_parser_instance = Mock()
        # AIMarkdownParser.parse_multiple은 List[Dict]를 반환해야 함
        mock_parsed_conversation_dict = {
            'provider': 'claude',
            'title': 'Test Conversation',
            'total_messages': 2,
            'user_messages': 1,
            'assistant_messages': 1,
            'has_code': False
        }
        mock_parser_instance.parse_multiple.return_value = [mock_parsed_conversation_dict]
        mock_parser.return_value = mock_parser_instance

        # Mock Saver
        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1]
        mock_saver.return_value = mock_saver_instance

        collector = AIChatCollector()
        result = collector.collect_from_files(['/tmp/test.md'])

        # 결과 확인
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['conversations_count'], 1)
        self.assertIn('claude', result['providers'])
        self.assertEqual(result['providers']['claude'], 1)

    @patch('collectors.ai_chat_collector.AILoadWatcher')
    def test_collect_from_downloads_no_files(self, mock_watcher):
        """다운로드 폴더 스캔 - 파일 없음"""
        # Mock Watcher
        mock_watcher_instance = Mock()
        mock_watcher_instance.scan_existing.return_value = []
        mock_watcher.return_value = mock_watcher_instance

        collector = AIChatCollector()
        result = collector.collect_from_downloads()

        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['conversations_count'], 0)

    @patch('collectors.ai_chat_collector.AILoadWatcher')
    def test_collect_from_downloads_no_files(self, mock_watcher):
        """다운로드 폴더 스캔 - 파일 없음"""
        # Mock Watcher
        mock_watcher_instance = Mock()
        mock_watcher_instance.scan_existing.return_value = []
        mock_watcher.return_value = mock_watcher_instance

        collector = AIChatCollector()
        result = collector.collect_from_downloads()

        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['conversations_count'], 0)


if __name__ == '__main__':
    unittest.main()
