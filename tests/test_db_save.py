#!/usr/bin/env python3
"""
DB 저장 테스트

원격 DB (SSH 터널)에 학습 아티팩트 저장 테스트
"""

import sys
from pathlib import Path
from datetime import date

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from storage.artifact_saver import ArtifactSaver
from load.github_load import GitHubLoader
from parse.github_parse import GitHubParser

def test_remote_db():
    """원격 DB 연결 및 저장 테스트"""
    print("="*60)
    print("DB 저장 테스트 (원격 서버)")
    print("="*60)

    # SSH 터널을 통한 원격 DB 접속
    # ssh -L 5432:localhost:5432 jcw@183.101.163.146
    # 위 명령을 먼저 실행해야 함

    db_config = {
        'host': 'localhost',  # SSH 터널 사용
        'port': 5432,
        'database': 'my_blog',
        'user': 'postgres',
        'password': 'postgres'
    }

    try:
        # 1. ArtifactSaver 초기화
        print("\n[1/4] ArtifactSaver 초기화...")
        saver = ArtifactSaver(db_config=db_config)

        # 2. GitHub 데이터 수집
        print("\n[2/4] GitHub 데이터 수집...")
        loader = GitHubLoader()
        commits = loader.load()

        if not commits:
            print("\n오늘 커밋이 없습니다. 테스트 데이터 사용...")
            test_commit = {
                'repo': 'LearningConvertedToPost',
                'sha': 'test123abc456',
                'message': 'Test commit for DB save\n\nThis is a test commit',
                'date': '2025-12-26T12:00:00Z',
                'url': 'https://github.com/cjang3285/LearningConvertedToPost/commit/test123',
                'files': [
                    {
                        'filename': 'test.py',
                        'status': 'added',
                        'additions': 5,
                        'deletions': 0,
                        'changes': 5,
                        'language': 'Python'
                    }
                ],
                'stats': {
                    'additions': 5,
                    'deletions': 0
                }
            }
            commits = [test_commit]

        # 3. 파싱
        print("\n[3/4] 데이터 파싱...")
        parser = GitHubParser()
        parsed_commits = parser.parse_commits(commits)

        # 4. DB 저장
        print("\n[4/4] DB에 저장...")
        for commit in commits[:3]:  # 최대 3개만 테스트
            artifact_id = saver.save_github_artifact(commit, date.today())
            print(f"  저장 완료: artifact_id={artifact_id}, sha={commit['sha'][:8]}")

        print("\n" + "="*60)
        print("[OK] DB 저장 테스트 성공!")
        print("="*60)

        # 5. 저장된 데이터 확인
        print("\n저장된 데이터 확인:")
        import psycopg2
        conn = psycopg2.connect(**db_config)
        try:
            with conn.cursor() as cur:
                # 오늘 저장된 아티팩트
                cur.execute("""
                    SELECT id, source_type, title, created_at
                    FROM learning.learning_artifacts
                    WHERE artifact_date = CURRENT_DATE
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                print("\n최근 저장된 아티팩트:")
                for row in rows:
                    print(f"  ID={row[0]}, {row[1]}: {row[2][:50]}")

                # GitHub 커밋 상세
                cur.execute("""
                    SELECT g.id, g.repo, g.sha, g.additions, g.deletions
                    FROM learning.github_commits g
                    JOIN learning.learning_artifacts a ON g.artifact_id = a.id
                    WHERE a.artifact_date = CURRENT_DATE
                    ORDER BY g.id DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                print("\nGitHub 커밋:")
                for row in rows:
                    print(f"  [{row[1]}] {row[2][:8]} (+{row[3]}/-{row[4]})")
        finally:
            conn.close()

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == '__main__':
    print("\n주의: SSH 터널이 필요합니다!")
    print("다른 터미널에서 실행:")
    print("  ssh -L 5432:localhost:5432 jcw@183.101.163.146")
    print()

    input("SSH 터널이 준비되면 Enter를 누르세요...")

    test_remote_db()
