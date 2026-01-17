#!/usr/bin/env python3
"""
GitHub 커밋 샘플 데이터에서 필요한 정보만 추출하는 통합 테스트

목적:
- 실제 GitHub API 응답에서 필요한 필드만 추출
- 언제, 무엇을, 어떻게(diff) 정보만 남기기
"""

import unittest
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_PATH = PROJECT_ROOT / 'tests' / 'fixtures' / 'github_commit_sample.json'


def extract_commit_info(commit_data: dict) -> dict:
    """
    커밋 데이터에서 필요한 정보만 추출

    필요한 정보:
    - 언제: commit.author.date
    - 무엇을: commit.message
    - 어떻게: files[].filename, files[].status, files[].patch

    Args:
        commit_data: GitHub API 커밋 응답 전체

    Returns:
        필요한 필드만 담긴 dict
    """
    # 1. 언제
    date = commit_data['commit']['author']['date']

    # 2. 무엇을
    message = commit_data['commit']['message']

    # 3. 어떻게 (파일 변경 사항)
    changes = []
    for file in commit_data.get('files', []):
        change = {
            'filename': file['filename'],
            'status': file['status'],
            'patch': file.get('patch', '')  # patch가 없을 수도 있음 (binary 파일 등)
        }
        changes.append(change)

    return {
        'date': date,
        'message': message,
        'changes': changes
    }


class TestGitHubCommitExtraction(unittest.TestCase):
    """GitHub 커밋 샘플 데이터 추출 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 전 샘플 데이터 로드"""
        with open(FIXTURE_PATH, 'r', encoding='utf-8') as f:
            cls.sample_data = json.load(f)

    def test_fixture_exists(self):
        """픽스처 파일 존재 확인"""
        self.assertTrue(FIXTURE_PATH.exists(), "github_commit_sample.json 파일이 없습니다")

    def test_extract_date(self):
        """날짜 추출 테스트"""
        extracted = extract_commit_info(self.sample_data)

        self.assertIn('date', extracted)
        self.assertEqual(extracted['date'], '2026-01-14T14:23:22Z')

        # 날짜 파싱 가능한지 확인
        parsed_date = datetime.fromisoformat(extracted['date'].replace('Z', '+00:00'))
        self.assertIsNotNone(parsed_date)

    def test_extract_message(self):
        """커밋 메시지 추출 테스트"""
        extracted = extract_commit_info(self.sample_data)

        self.assertIn('message', extracted)
        self.assertIn('Merge pull request', extracted['message'])
        self.assertIn('replace export with load', extracted['message'])

    def test_extract_changes(self):
        """파일 변경 사항 추출 테스트"""
        extracted = extract_commit_info(self.sample_data)

        self.assertIn('changes', extracted)
        self.assertIsInstance(extracted['changes'], list)
        self.assertGreater(len(extracted['changes']), 0, "변경된 파일이 없습니다")

        # 첫 번째 파일 검증
        first_change = extracted['changes'][0]
        self.assertIn('filename', first_change)
        self.assertIn('status', first_change)
        self.assertIn('patch', first_change)

        # 실제 데이터 확인
        self.assertEqual(first_change['filename'], 'How_daemon_works.md')
        self.assertEqual(first_change['status'], 'modified')
        self.assertIn('LearningCollector', first_change['patch'])

    def test_extracted_structure(self):
        """추출된 데이터 구조 전체 검증"""
        extracted = extract_commit_info(self.sample_data)

        # 필수 필드만 있는지 확인
        self.assertEqual(set(extracted.keys()), {'date', 'message', 'changes'})

        # 각 change에 필요한 필드만 있는지 확인
        for change in extracted['changes']:
            self.assertEqual(set(change.keys()), {'filename', 'status', 'patch'})

    def test_no_extra_fields(self):
        """불필요한 필드가 제거되었는지 확인"""
        extracted = extract_commit_info(self.sample_data)

        # 제거되어야 할 필드들
        unwanted_fields = ['sha', 'node_id', 'url', 'html_url', 'author', 'committer',
                          'parents', 'stats', 'verification']

        for field in unwanted_fields:
            self.assertNotIn(field, extracted)

    def test_print_extracted_sample(self):
        """추출된 샘플 출력 (디버깅용)"""
        extracted = extract_commit_info(self.sample_data)

        print("\n" + "="*60)
        print("추출된 커밋 정보 (필요한 필드만)")
        print("="*60)
        print(json.dumps(extracted, indent=2, ensure_ascii=False))
        print("="*60)
        print(f"\n총 {len(extracted['changes'])}개 파일 변경됨")

        # 변경 통계
        status_count = {}
        for change in extracted['changes']:
            status = change['status']
            status_count[status] = status_count.get(status, 0) + 1

        print("\n파일 변경 통계:")
        for status, count in status_count.items():
            print(f"  - {status}: {count}개")


if __name__ == '__main__':
    unittest.main(verbosity=2)
