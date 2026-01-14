#!/usr/bin/env python3
"""
E2E 통합 테스트

전체 파이프라인 동작을 검증합니다:
- 다운로드 폴더 감시 → 마크다운 파싱 → DB 저장
- GitHub/Baekjoon/AI Chat 전체 워크플로우
"""

import unittest
import sys
import os
import time
import shutil
import tempfile
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from load.ai_chat_load import AILoadWatcher, AIMarkdownHandler
from collectors.ai_chat_collector import AIChatCollector
from parse.ai_chat_parse import AIMarkdownParser


class TestAILoadWatcherRealFileSystem(unittest.TestCase):
    """AILoadWatcher 실제 파일 시스템 테스트"""

    def setUp(self):
        """테스트 전 임시 디렉토리 설정"""
        self.temp_download_dir = tempfile.mkdtemp(prefix='test_downloads_')
        self.temp_target_dir = tempfile.mkdtemp(prefix='test_target_')

    def tearDown(self):
        """테스트 후 임시 디렉토리 정리"""
        shutil.rmtree(self.temp_download_dir, ignore_errors=True)
        shutil.rmtree(self.temp_target_dir, ignore_errors=True)

    def test_scan_existing_files(self):
        """다운로드 폴더에서 기존 AI 채팅 파일 스캔"""
        # 테스트 마크다운 파일 생성
        test_files = [
            'Claude-Export-2025-12-29.md',
            'ChatGPT-Export-2025-12-29.md',
            'Gemini-Chat-2025-12-29.md',
            'normal-file.md'  # 이건 스캔되지 않아야 함
        ]

        for filename in test_files:
            file_path = Path(self.temp_download_dir) / filename
            file_path.write_text(f"# Test {filename}\n\nTest content")

        # Watcher 생성 및 스캔
        watcher = AILoadWatcher(
            download_dir=self.temp_download_dir,
            target_dir=self.temp_target_dir
        )

        ai_files = watcher.scan_existing()

        # 검증
        self.assertEqual(len(ai_files), 3)  # Claude, ChatGPT, Gemini만
        ai_filenames = [f.name for f in ai_files]
        self.assertIn('Claude-Export-2025-12-29.md', ai_filenames)
        self.assertIn('ChatGPT-Export-2025-12-29.md', ai_filenames)
        self.assertIn('Gemini-Chat-2025-12-29.md', ai_filenames)
        self.assertNotIn('normal-file.md', ai_filenames)

    def test_collect_existing_files_with_callback(self):
        """기존 파일 수집 및 콜백 호출 테스트"""
        # 테스트 파일 생성
        test_file = Path(self.temp_download_dir) / 'Claude-Test-2025.md'
        test_file.write_text("# Test Conversation\n\nTest content")

        # 콜백 Mock
        callback_mock = Mock()

        # Watcher 생성 및 수집
        watcher = AILoadWatcher(
            download_dir=self.temp_download_dir,
            target_dir=self.temp_target_dir
        )

        count = watcher.collect_existing(callback=callback_mock)

        # 검증
        self.assertEqual(count, 1)
        callback_mock.assert_called_once()

        # 타겟 디렉토리에 파일이 복사되었는지 확인
        target_files = list(Path(self.temp_target_dir).glob('*.md'))
        self.assertEqual(len(target_files), 1)
        self.assertIn('Claude-Test-2025', target_files[0].name)

    def test_file_handler_filtering(self):
        """AIMarkdownHandler 파일 필터링 테스트"""
        handler = AIMarkdownHandler(
            download_dir=self.temp_download_dir,
            target_dir=self.temp_target_dir
        )

        # AI 채팅 파일 테스트
        self.assertTrue(handler.is_ai_chat_file(Path('Claude-Export.md')))
        self.assertTrue(handler.is_ai_chat_file(Path('ChatGPT-Conversation.md')))
        self.assertTrue(handler.is_ai_chat_file(Path('Gemini-Chat.md')))

        # 일반 파일 테스트
        self.assertFalse(handler.is_ai_chat_file(Path('README.md')))
        self.assertFalse(handler.is_ai_chat_file(Path('test.txt')))
        self.assertFalse(handler.is_ai_chat_file(Path('claude.md')))  # 소문자


class TestAIChatE2EWorkflow(unittest.TestCase):
    """AI Chat 전체 워크플로우 E2E 테스트"""

    def setUp(self):
        """테스트 전 임시 디렉토리 설정"""
        self.temp_download_dir = tempfile.mkdtemp(prefix='test_ai_chat_')

    def tearDown(self):
        """테스트 후 임시 디렉토리 정리"""
        shutil.rmtree(self.temp_download_dir, ignore_errors=True)

    @patch('collectors.ai_chat_collector.AIChatSaver')
    def test_full_pipeline_download_to_db(self, mock_saver):
        """다운로드 폴더 → 파싱 → DB 저장 전체 파이프라인"""
        # 1. 테스트 마크다운 파일 생성 (Claude 형식)
        test_content = """# Test Conversation

**User:**
Hello, how are you?

**Assistant:**
I'm doing well, thank you for asking!

**User:**
Can you help me with Python?

**Assistant:**
Of course! I'd be happy to help with Python.
"""

        test_file = Path(self.temp_download_dir) / 'Claude-Test.md'
        test_file.write_text(test_content)

        # 2. Mock Saver 설정
        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1, 2, 3]  # 3개 저장됨
        mock_saver.return_value = mock_saver_instance

        # 3. Collector로 수집
        collector = AIChatCollector()
        result = collector.collect_from_downloads(
            download_dir=self.temp_download_dir
        )

        # 4. 검증
        self.assertTrue(result['success'])
        self.assertGreater(result['conversations_count'], 0)
        self.assertIn('artifact_ids', result)


class TestGitHubE2EWorkflow(unittest.TestCase):
    """GitHub 전체 워크플로우 E2E 테스트"""

    @patch('collectors.github_collector.GitHubSaver')
    @patch('collectors.github_collector.GitHubParser')
    @patch('collectors.github_collector.GitHubLoader')
    def test_github_export_parse_save_pipeline(self, mock_exporter, mock_parser, mock_saver):
        """GitHub Export → Parse → Save 파이프라인"""
        # Mock 설정
        mock_exp_instance = Mock()
        mock_exp_instance.load.return_value = [
            {
                'repo': 'test-repo',
                'sha': 'abc123',
                'message': 'Test commit',
                'date': '2025-12-29T12:00:00Z',
                'url': 'https://github.com/test/repo/commit/abc123',
                'stats': {'additions': 10, 'deletions': 5},
                'files': []
            }
        ]
        mock_exporter.return_value = mock_exp_instance

        mock_parser_instance = Mock()
        mock_commit = Mock()
        mock_commit.repo = 'test-repo'
        mock_commit.sha = 'abc123'
        mock_parser_instance.parse_commits.return_value = [mock_commit]
        mock_parser.return_value = mock_parser_instance

        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1]
        mock_saver.return_value = mock_saver_instance

        # Collector 실행
        from collectors.github_collector import GitHubCollector
        from interfaces import CollectionContext, CollectionResult
        collector = GitHubCollector()
        context = CollectionContext(target_date=date.today(), options={})
        result = collector.collect(context)

        # 검증
        self.assertIsInstance(result, CollectionResult)
        self.assertTrue(result.success)


class TestBaekjoonE2EWorkflow(unittest.TestCase):
    """백준 전체 워크플로우 E2E 테스트"""

    @patch('collectors.baekjoon_collector.BaekjoonSaver')
    @patch('collectors.baekjoon_collector.BaekjoonParser')
    @patch('collectors.baekjoon_collector.BaekjoonLoader')
    def test_baekjoon_export_parse_save_pipeline(self, mock_exporter, mock_parser, mock_saver):
        """백준 Export → Parse → Save 파이프라인"""
        # Mock 설정
        mock_exp_instance = Mock()
        mock_exp_instance.load.return_value = [
            {
                'readme_path': '백준/Silver/1000. A+B/README.md',
                'code_path': '백준/Silver/1000. A+B/A+B.py',
                'commit_sha': 'def456',
                'tier': 'Silver',
                'problem_folder': '1000. A+B'
            }
        ]
        mock_exporter.return_value = mock_exp_instance

        mock_parser_instance = Mock()
        mock_problem = Mock()
        mock_problem.problem_id = 1000
        mock_parser_instance.parse_problems.return_value = [mock_problem]
        mock_parser.return_value = mock_parser_instance

        mock_saver_instance = Mock()
        mock_saver_instance.save_all.return_value = [1]
        mock_saver.return_value = mock_saver_instance

        # Collector 실행
        from collectors.baekjoon_collector import BaekjoonCollector
        from interfaces import CollectionContext, CollectionResult
        collector = BaekjoonCollector()
        context = CollectionContext(target_date=date.today(), options={})
        result = collector.collect(context)

        # 검증
        self.assertIsInstance(result, CollectionResult)
        self.assertTrue(result.success)


class TestMainETLPipeline(unittest.TestCase):
    """메인 ETL 파이프라인 통합 테스트"""

    @patch('main.BaekjoonCollector')
    @patch('main.AIChatCollector')
    @patch('main.ClaudeMigrationCollector')
    @patch('main.GitHubCollector')
    def test_main_etl_run_all_collectors(self, mock_github, mock_claude, mock_ai_chat, mock_baekjoon):
        """메인 ETL 실행 - 모든 Collector 동작"""
        # Mock 설정
        for mock_collector_class in [mock_github, mock_claude, mock_ai_chat, mock_baekjoon]:
            mock_instance = Mock()
            mock_instance.collect.return_value = {
                'success': True,
                'commits_count': 5,
                'conversations_count': 3,
                'solutions_count': 2
            }
            mock_collector_class.return_value = mock_instance

        # ETL 실행
        from main import LearningETL
        etl = LearningETL()
        result = etl.run(date.today())

        # 검증
        self.assertIsInstance(result, dict)
        self.assertIn('summary', result)
        self.assertIn('total_artifacts', result['summary'])
        self.assertTrue(result['summary']['success'])


if __name__ == '__main__':
    unittest.main()
