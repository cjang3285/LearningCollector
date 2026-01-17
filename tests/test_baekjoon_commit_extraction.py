#!/usr/bin/env python3
"""
백준허브 커밋 샘플 데이터에서 필요한 정보만 추출하는 통합 테스트

목적:
- 실제 GitHub API 응답에서 필요한 필드만 추출
- 어떤 문제인지 + 어떻게 푼건지(코드+주석) 정보만 남기기
"""

import unittest
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_PATH = PROJECT_ROOT / 'tests' / 'fixtures' / 'baekjoon_commit_sample.json'


def extract_problem_info_from_readme(patch: str) -> dict:
    """
    README.md patch에서 문제 정보 추출

    Args:
        patch: README.md 파일의 patch 내용

    Returns:
        문제 정보 dict
    """
    # 제목 라인에서 tier, title, number 추출
    # "# [Silver II] 랜선 자르기 - 1654"
    title_match = re.search(r'\+# \[(.+?)\] (.+?) - (\d+)', patch)

    tier = title_match.group(1) if title_match else ""
    title = title_match.group(2) if title_match else ""
    number = title_match.group(3) if title_match else ""

    # 분류(태그) 추출
    # "+이분 탐색, 매개 변수 탐색"
    tags = []
    tags_match = re.search(r'\+### 분류\n\+\n\+(.+)', patch)
    if tags_match:
        tags_text = tags_match.group(1)
        tags = [tag.strip() for tag in tags_text.split(',')]

    return {
        'tier': tier,
        'number': number,
        'title': title,
        'tags': tags
    }


def extract_comments_from_code(patch: str) -> list:
    """
    코드 patch에서 주석만 추출

    Args:
        patch: 코드 파일의 patch 내용

    Returns:
        주석 리스트
    """
    comments = []

    # patch에서 추가된 라인(+로 시작)만 추출
    for line in patch.split('\n'):
        if not line.startswith('+'):
            continue

        # + 제거하고 끝의 \r도 제거
        code_line = line[1:].replace('\\r', '')

        # C++ 한줄 주석 (//)
        if '//' in code_line:
            comment = code_line[code_line.index('//'):].strip()
            comments.append(comment)

        # C++ 여러줄 주석 (/* */)
        # 간단히 처리: /* 포함된 라인 전체를 주석으로
        elif '/*' in code_line or '*/' in code_line:
            comments.append(code_line.strip())

    return comments


def extract_full_code_from_patch(patch: str) -> str:
    """
    patch에서 전체 코드 추출 (추가된 라인만)

    Args:
        patch: 코드 파일의 patch 내용

    Returns:
        전체 코드 문자열
    """
    code_lines = []

    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            # + 제거하고 끝의 \r도 제거
            code_line = line[1:].replace('\\r', '')
            code_lines.append(code_line)

    return '\n'.join(code_lines)


def extract_baekjoon_commit_info(commit_data: dict) -> dict:
    """
    백준허브 커밋 데이터에서 필요한 정보만 추출

    필요한 정보:
    - 언제: commit.author.date
    - 어떤 문제: README.md에서 추출 (tier, number, title, tags)
    - 어떻게 풀었는지: 코드 파일에서 추출 (code, comments)

    Args:
        commit_data: GitHub API 커밋 응답 전체

    Returns:
        필요한 필드만 담긴 dict
    """
    # 1. 언제
    date = commit_data['commit']['author']['date']

    # 2. 파일 분류
    readme_file = None
    code_file = None

    for file in commit_data.get('files', []):
        filename = file['filename']
        if filename.endswith('README.md'):
            readme_file = file
        elif not filename.endswith('README.md'):  # 코드 파일
            code_file = file

    # 3. 문제 정보 추출
    problem_info = {}
    if readme_file:
        problem_info = extract_problem_info_from_readme(readme_file.get('patch', ''))

    # 4. 코드 정보 추출
    solution = {}
    if code_file:
        solution = {
            'filename': code_file['filename'].split('/')[-1],  # 파일명만
            'code': extract_full_code_from_patch(code_file.get('patch', '')),
            'comments': extract_comments_from_code(code_file.get('patch', ''))
        }

    return {
        'date': date,
        'problem': problem_info,
        'solution': solution
    }


class TestBaekjoonCommitExtraction(unittest.TestCase):
    """백준허브 커밋 샘플 데이터 추출 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 전 샘플 데이터 로드"""
        with open(FIXTURE_PATH, 'r', encoding='utf-8') as f:
            cls.sample_data = json.load(f)

    def test_fixture_exists(self):
        """픽스처 파일 존재 확인"""
        self.assertTrue(FIXTURE_PATH.exists(), "baekjoon_commit_sample.json 파일이 없습니다")

    def test_extract_date(self):
        """날짜 추출 테스트"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        self.assertIn('date', extracted)
        self.assertEqual(extracted['date'], '2026-01-16T10:14:45Z')

    def test_extract_problem_info(self):
        """문제 정보 추출 테스트"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        self.assertIn('problem', extracted)
        problem = extracted['problem']

        self.assertEqual(problem['tier'], 'Silver II')
        self.assertEqual(problem['number'], '1654')
        self.assertEqual(problem['title'], '랜선 자르기')
        self.assertIn('이분 탐색', problem['tags'])
        self.assertIn('매개 변수 탐색', problem['tags'])

    def test_extract_solution_code(self):
        """풀이 코드 추출 테스트"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        self.assertIn('solution', extracted)
        solution = extracted['solution']

        self.assertIn('filename', solution)
        self.assertEqual(solution['filename'], '랜선 자르기.cc')

        self.assertIn('code', solution)
        self.assertGreater(len(solution['code']), 0)
        self.assertIn('int main()', solution['code'])

    def test_extract_comments(self):
        """주석 추출 테스트"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        comments = extracted['solution']['comments']
        self.assertIsInstance(comments, list)
        self.assertGreater(len(comments), 0, "주석이 없습니다")

        # 실제 주석 내용 확인
        comment_text = '\n'.join(comments)
        self.assertIn('범위 설정', comment_text)
        self.assertIn('중앙값', comment_text)
        self.assertIn('low', comment_text)

    def test_extracted_structure(self):
        """추출된 데이터 구조 전체 검증"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        # 필수 필드 확인
        self.assertEqual(set(extracted.keys()), {'date', 'problem', 'solution'})

        # problem 필드
        self.assertEqual(set(extracted['problem'].keys()),
                        {'tier', 'number', 'title', 'tags'})

        # solution 필드
        self.assertEqual(set(extracted['solution'].keys()),
                        {'filename', 'code', 'comments'})

    def test_no_extra_fields(self):
        """불필요한 필드가 제거되었는지 확인"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        # 제거되어야 할 필드들
        unwanted_fields = ['sha', 'node_id', 'url', 'html_url', 'author',
                          'committer', 'parents', 'stats', 'verification']

        for field in unwanted_fields:
            self.assertNotIn(field, extracted)

    def test_print_extracted_sample(self):
        """추출된 샘플 출력 (디버깅용)"""
        extracted = extract_baekjoon_commit_info(self.sample_data)

        print("\n" + "="*60)
        print("추출된 백준 풀이 정보 (필요한 필드만)")
        print("="*60)

        # 주석이 너무 길어서 일부만 출력
        display_data = extracted.copy()
        if len(display_data['solution']['comments']) > 5:
            display_data['solution']['comments'] = \
                display_data['solution']['comments'][:5] + ['...']

        # 코드도 너무 길어서 일부만
        code_lines = display_data['solution']['code'].split('\n')
        if len(code_lines) > 20:
            display_data['solution']['code'] = \
                '\n'.join(code_lines[:20]) + '\n... (생략)'

        print(json.dumps(display_data, indent=2, ensure_ascii=False))
        print("="*60)

        # 통계
        print(f"\n문제: [{extracted['problem']['tier']}] "
              f"{extracted['problem']['number']}. {extracted['problem']['title']}")
        print(f"태그: {', '.join(extracted['problem']['tags'])}")
        print(f"주석: {len(extracted['solution']['comments'])}개")
        print(f"코드: {len(extracted['solution']['code'])}자")


if __name__ == '__main__':
    unittest.main(verbosity=2)
