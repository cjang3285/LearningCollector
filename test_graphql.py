#!/usr/bin/env python3
"""
GraphQL API 테스트 스크립트
실제로 커밋이 수집되는지 확인
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from api.github_graphql import GitHubGraphQLClient

def test_recent_commits():
    """최근 1시간 커밋 조회 테스트"""
    print("=" * 60)
    print("GraphQL API 테스트: 최근 1시간 커밋 조회")
    print("=" * 60)

    client = GitHubGraphQLClient()
    username = os.getenv("GITHUB_USERNAME")

    # 최근 1시간
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=1)

    print(f"\n사용자: {username}")
    print(f"수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    commits = client.fetch_commits(username, start_date, end_date)

    print(f"\n{'='*60}")
    print(f"결과: 총 {len(commits)}개 커밋")
    print(f"{'='*60}")

    if commits:
        print("\n수집된 커밋 목록:")
        for i, commit in enumerate(commits, 1):
            print(f"\n{i}. {commit['repository']} ({commit['oid'][:7]})")
            print(f"   메시지: {commit['message'][:60]}")
            print(f"   날짜: {commit['committedDate']}")
    else:
        print("\n⚠️  커밋이 수집되지 않았습니다!")
        print("\n가능한 원인:")
        print("1. 실제로 최근 1시간 내 커밋이 없음")
        print("2. GraphQL API 에러 (위 로그 확인)")
        print("3. GITHUB_TOKEN 권한 문제")
        print("4. since 파라미터 이슈")

def test_specific_repo():
    """특정 레포의 최근 7일 커밋 조회"""
    print("\n" + "=" * 60)
    print("GraphQL API 테스트: LearningCollector 최근 7일")
    print("=" * 60)

    client = GitHubGraphQLClient()
    username = os.getenv("GITHUB_USERNAME")

    # 최근 7일
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"\n사용자: {username}")
    print(f"수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    commits = client.fetch_commits(username, start_date, end_date)

    # LearningCollector만 필터링
    learning_commits = [c for c in commits if c['repository'] == 'LearningCollector']

    print(f"\n{'='*60}")
    print(f"결과: LearningCollector 레포에서 {len(learning_commits)}개 커밋")
    print(f"{'='*60}")

    if learning_commits:
        print("\n최근 10개 커밋:")
        for i, commit in enumerate(learning_commits[:10], 1):
            print(f"\n{i}. {commit['oid'][:7]} - {commit['message'][:60]}")
            print(f"   날짜: {commit['committedDate']}")

if __name__ == "__main__":
    # 테스트 1: 최근 1시간
    test_recent_commits()

    # 테스트 2: LearningCollector 최근 7일
    test_specific_repo()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
