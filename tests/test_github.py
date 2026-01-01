#!/usr/bin/env python3
"""
GitHub 모듈 테스트
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from export.github_export import GitHubExporter
from parse.github_parse import GitHubParser


class TestGitHubModuleIntegration(unittest.TestCase):
    """GitHub 모듈 통합 테스트 (Export + Parse)"""

    @patch('export.github_export.GitHubExporter.get_user_repos')
    @patch('export.github_export.GitHubExporter.get_commits_by_date')
    @patch('export.github_export.GitHubExporter.get_commit_detail')
    @patch('export.github_export.GitHubExporter.get_file_content')
    def test_github_workflow(self, mock_get_file_content, mock_get_commit_detail,
                             mock_get_commits_by_date, mock_get_user_repos):
        """GitHub Export와 Parse 모듈의 통합 워크플로우 테스트"""

        # Mocking setup for Exporter
        mock_get_user_repos.return_value = [
            {'name': 'repo1', 'owner': {'login': 'testuser'}},
            {'name': 'repo2', 'owner': {'login': 'testuser'}}
        ]

        mock_get_commits_by_date.side_effect = [
            [{'sha': 'sha1_repo1', 'commit': {'message': 'commit 1 repo1', 'author': {'date': '2026-01-01T10:00:00Z'}}, 'html_url': 'http://example.com/repo1'}],
            [{'sha': 'sha1_repo2', 'commit': {'message': 'commit 1 repo2', 'author': {'date': '2026-01-01T11:00:00Z'}}, 'html_url': 'http://example.com/repo2'}]
        ]

        mock_get_commit_detail.side_effect = [
            {'files': [{'filename': 'file1.py', 'status': 'added', 'additions': 10, 'deletions': 0, 'changes': 10, 'patch': 'patch1'}], 'stats': {'total': 10, 'additions': 10, 'deletions': 0}},
            {'files': [{'filename': 'file2.js', 'status': 'modified', 'additions': 5, 'deletions': 2, 'changes': 7, 'patch': 'patch2'}], 'stats': {'total': 7, 'additions': 5, 'deletions': 2}}
        ]
        mock_get_file_content.side_effect = ["print('hello')", "console.log('world')"]

        # 1. Export 테스트
        print("\n[1/2] GitHub Export 테스트...")
        exporter = GitHubExporter(token='test_token', usernames=['testuser'])
        commits = exporter.export()

        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]['repo'], 'repo1')
        self.assertEqual(commits[1]['repo'], 'repo2')
        self.assertIn('files', commits[0])
        self.assertIn('content', commits[0]['files'][0])
        self.assertEqual(commits[0]['files'][0]['content'], "print('hello')")

        # 2. Parse 테스트
        print("\n[2/2] GitHub Parse 테스트...")
        parser = GitHubParser()
        parsed_commits = parser.parse_commits(commits)
        summary = parser.get_summary(parsed_commits)

        self.assertEqual(summary['total_commits'], 2)
        self.assertEqual(summary['total_repos'], 2)
        self.assertEqual(summary['total_files'], 2)
        self.assertEqual(summary['total_additions'], 15)
        self.assertEqual(summary['total_deletions'], 2)
        self.assertIn('Python', summary['languages'])
        self.assertIn('JavaScript', summary['languages'])
        self.assertEqual(summary['languages']['Python'], 1)
        self.assertEqual(summary['languages']['JavaScript'], 1)
        # Note: 'total_comments' is hard to test accurately with generic mock data, so we'll omit a specific assertion for now

        print("\n[OK] 테스트 완료")


if __name__ == '__main__':
    unittest.main()
