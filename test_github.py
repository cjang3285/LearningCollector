#!/usr/bin/env python3
"""
GitHub 모듈 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from export.github_export import GitHubExporter
from parse.github_parse import GitHubParser

def test_github():
    print("="*60)
    print("GitHub 모듈 테스트")
    print("="*60)

    try:
        # Export 테스트
        print("\n[1/2] GitHub Export 테스트...")
        exporter = GitHubExporter()
        commits = exporter.export_today()

        print(f"\n수집된 커밋: {len(commits)}개")

        if commits:
            # Parse 테스트
            print("\n[2/2] GitHub Parse 테스트...")
            parser = GitHubParser()
            parsed_commits = parser.parse_commits(commits)
            summary = parser.get_summary(parsed_commits)

            print("\n--- 요약 ---")
            print(f"총 커밋: {summary['total_commits']}개")
            print(f"저장소: {summary['total_repos']}개")
            print(f"파일: {summary['total_files']}개")
            print(f"추가 라인: +{summary['total_additions']}")
            print(f"삭제 라인: -{summary['total_deletions']}")
            print(f"언어별 파일 수: {summary['languages']}")
            print(f"주석: {summary['total_comments']}개")

            print("\n--- 커밋 상세 ---")
            for commit in parsed_commits[:3]:  # 최대 3개만 출력
                print(f"\n[{commit.repo}] {commit.message[:50]}")
                print(f"  SHA: {commit.sha[:8]}")
                print(f"  날짜: {commit.date}")
                print(f"  파일: {len(commit.files)}개")
                for file in commit.files[:2]:  # 각 커밋당 최대 2개 파일만
                    print(f"    - {file.filename} ({file.language})")
                    print(f"      {file.status}: +{file.additions}/-{file.deletions}")
                    if file.comments:
                        print(f"      주석: {len(file.comments)}개")
        else:
            print("\n오늘 커밋이 없습니다.")

        print("\n" + "="*60)
        print("[OK] 테스트 완료")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_github()
