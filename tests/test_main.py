#!/usr/bin/env python3
"""
Main ETL Pipeline 테스트

LearningETL 메인 클래스 및 전체 파이프라인을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import LearningETL


class TestLearningETL(unittest.TestCase):
    """LearningETL 메인 클래스 테스트"""

    @patch('main.COLLECT_GITHUB', False)
    @patch('main.COLLECT_CLAUDE', False)
    @patch('main.COLLECT_BAEKJOON', False)
    def test_init_without_collectors(self):
        """Collector 없이 초기화 테스트"""
        etl = LearningETL()

        # 모든 collector가 None이어야 함
        self.assertIsNone(etl.github_collector)
        self.assertIsNone(etl.claude_collector)
        self.assertIsNone(etl.baekjoon_collector)

    @patch('main.GitHubCollector')
    @patch('main.ClaudeCollector')
    @patch('main.BaekjoonCollector')
    @patch('main.COLLECT_GITHUB', True)
    @patch('main.COLLECT_CLAUDE', True)
    @patch('main.COLLECT_BAEKJOON', True)
    def test_init_with_all_collectors(self, mock_boj, mock_claude, mock_github):
        """모든 Collector와 함께 초기화 테스트"""
        # Mock 설정
        mock_github.return_value = Mock()
        mock_claude.return_value = Mock()
        mock_boj.return_value = Mock()

        etl = LearningETL()

        # 모든 collector가 생성되어야 함
        self.assertIsNotNone(etl.github_collector)
        self.assertIsNotNone(etl.claude_collector)
        self.assertIsNotNone(etl.baekjoon_collector)

    @patch('main.COLLECT_GITHUB', False)
    @patch('main.COLLECT_CLAUDE', False)
    @patch('main.COLLECT_BAEKJOON', False)
    def test_run_without_collectors(self):
        """Collector 없이 실행 테스트"""
        etl = LearningETL()
        result = etl.run(date.today())

        # 결과는 dict여야 함
        self.assertIsInstance(result, dict)
        self.assertIn('date', result)
        self.assertIn('timestamp', result)
        self.assertIn('summary', result)

        # 모든 결과가 None이어야 함
        self.assertIsNone(result['github'])
        self.assertIsNone(result['claude'])
        self.assertIsNone(result['baekjoon'])

    @patch('main.GitHubCollector')
    @patch('main.COLLECT_GITHUB', True)
    @patch('main.COLLECT_CLAUDE', False)
    @patch('main.COLLECT_BAEKJOON', False)
    def test_run_with_github_only(self, mock_github):
        """GitHub만 활성화하고 실행 테스트"""
        # Mock GitHub Collector
        mock_collector = Mock()
        mock_collector.collect.return_value = {
            'success': True,
            'count': 5
        }
        mock_github.return_value = mock_collector

        etl = LearningETL()
        result = etl.run(date.today())

        # GitHub 결과만 있어야 함
        self.assertIsNotNone(result['github'])
        self.assertIsNone(result['claude'])
        self.assertIsNone(result['baekjoon'])

        # collect 메서드가 호출되었는지 확인
        mock_collector.collect.assert_called_once()

    @patch('main.ClaudeCollector')
    @patch('main.COLLECT_GITHUB', False)
    @patch('main.COLLECT_CLAUDE', True)
    @patch('main.COLLECT_BAEKJOON', False)
    def test_run_with_claude_zip(self, mock_claude):
        """Claude ZIP 파일과 함께 실행 테스트"""
        # Mock Claude Collector
        mock_collector = Mock()
        mock_collector.collect.return_value = {
            'success': True,
            'count': 3
        }
        mock_claude.return_value = mock_collector

        etl = LearningETL()
        test_zip_path = '/tmp/test.zip'
        result = etl.run(date.today(), claude_zip_path=test_zip_path)

        # Claude 결과가 있어야 함
        self.assertIsNotNone(result['claude'])

        # collect 메서드가 ZIP 경로와 함께 호출되었는지 확인
        mock_collector.collect.assert_called_once()

    def test_run_returns_summary(self):
        """실행 결과에 요약 정보가 포함되는지 확인"""
        with patch('main.COLLECT_GITHUB', False), \
             patch('main.COLLECT_CLAUDE', False), \
             patch('main.COLLECT_BAEKJOON', False):

            etl = LearningETL()
            result = etl.run(date.today())

            # 요약 정보 확인
            self.assertIn('summary', result)
            self.assertIsInstance(result['summary'], dict)


if __name__ == '__main__':
    unittest.main()
