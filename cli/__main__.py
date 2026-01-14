#!/usr/bin/env python3
"""
개인 학습 정보 수집 CLI - 데이터 조회 도구

사용법:
    python cli.py stats                    # 전체 통계
    python cli.py list github              # GitHub 커밋 목록
    python cli.py list ai-chat             # AI 채팅 목록
    python cli.py list baekjoon            # 백준 풀이 목록
    python cli.py show github <sha>        # 커밋 상세
    python cli.py export --date 2025-12-29 # 데이터 내보내기
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from datetime import date, datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


class LearningCLI:
    """개인 학습 정보 수집 CLI"""

    def __init__(self):
        self.conn = None

    def connect(self):
        """DB 연결"""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            return True
        except Exception as e:
            print(f"[ERROR] DB 연결 실패: {e}")
            return False

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()

    def stats(self):
        """전체 통계"""
        print("="*60)
        print("개인 학습 정보 수집 통계")
        print("="*60)
        print()

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 전체 아티팩트
            cur.execute("""
                SELECT
                    source_type,
                    COUNT(*) as count,
                    MIN(artifact_date) as first_date,
                    MAX(artifact_date) as last_date
                FROM learning.learning_artifacts
                GROUP BY source_type
                ORDER BY count DESC
            """)
            artifacts = cur.fetchall()

            print("전체 아티팩트")
            print()
            total = 0
            for row in artifacts:
                count = row['count']
                total += count
                print(f"  {row['source_type']:15} {count:5}개  ({row['first_date']} ~ {row['last_date']})")
            print(f"  {'TOTAL':15} {total:5}개")
            print()

            # 최근 7일 통계
            print("최근 7일")
            print()
            cur.execute("""
                SELECT
                    artifact_date,
                    source_type,
                    COUNT(*) as count
                FROM learning.learning_artifacts
                WHERE artifact_date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY artifact_date, source_type
                ORDER BY artifact_date DESC, source_type
            """)
            recent = cur.fetchall()

            current_date = None
            for row in recent:
                if row['artifact_date'] != current_date:
                    if current_date is not None:
                        print()
                    current_date = row['artifact_date']
                    print(f"  {current_date}:")
                print(f"    {row['source_type']:15} {row['count']:3}개")

            if not recent:
                print("  (데이터 없음)")

            print()

            # GitHub 통계
            cur.execute("""
                SELECT
                    COUNT(*) as total_commits,
                    COUNT(DISTINCT repo) as total_repos,
                    SUM(additions) as total_additions,
                    SUM(deletions) as total_deletions
                FROM learning.github_commits
            """)
            github = cur.fetchone()

            if github and github['total_commits']:
                print("GitHub")
                print()
                print(f"  커밋: {github['total_commits']}개")
                print(f"  레포: {github['total_repos']}개")
                print(f"  추가: +{github['total_additions']:,} 줄")
                print(f"  삭제: -{github['total_deletions']:,} 줄")

                # 최근 5개 커밋
                cur.execute("""
                    SELECT
                        message,
                        repo,
                        commit_date
                    FROM learning.github_commits
                    ORDER BY commit_date DESC
                    LIMIT 5
                """)
                recent_commits = cur.fetchall()

                if recent_commits:
                    print()
                    print("  최근 커밋:")
                    for c in recent_commits:
                        msg = c['message'].split('\n')[0][:50]
                        print(f"    [{c['commit_date']}] {c['repo']:20} {msg}")

                print()

            # AI 채팅 통계
            cur.execute("""
                SELECT
                    provider,
                    COUNT(*) as count
                FROM learning.ai_chat_conversations
                GROUP BY provider
                ORDER BY count DESC
            """)
            ai_chats = cur.fetchall()

            if ai_chats:
                print("AI 채팅")
                print()
                for row in ai_chats:
                    print(f"  {row['provider']:10} {row['count']:3}개")
                print()

            # 백준 통계
            cur.execute("""
                SELECT
                    COUNT(*) as total_problems,
                    COUNT(DISTINCT tier) as tiers
                FROM learning.baekjoon_solutions
            """)
            baekjoon = cur.fetchone()

            if baekjoon and baekjoon['total_problems']:
                print("백준")
                print()
                print(f"  문제: {baekjoon['total_problems']}개")

                # 최근 5개 문제
                cur.execute("""
                    SELECT
                        bs.problem_id,
                        bs.title,
                        bs.tier,
                        la.artifact_date
                    FROM learning.baekjoon_solutions bs
                    JOIN learning.learning_artifacts la ON bs.artifact_id = la.id
                    ORDER BY la.artifact_date DESC
                    LIMIT 5
                """)
                recent_problems = cur.fetchall()

                if recent_problems:
                    print()
                    print("  최근 풀이:")
                    for p in recent_problems:
                        print(f"    {p['problem_id']:5} {p['title'][:30]:30} [{p['tier']}] {p['artifact_date']}")

                print()

        print("="*60)

    def list_items(self, item_type, limit=20):
        """항목 목록"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            if item_type == 'github':
                cur.execute("""
                    SELECT
                        sha,
                        repo,
                        message,
                        commit_date,
                        additions,
                        deletions
                    FROM learning.github_commits
                    ORDER BY commit_date DESC
                    LIMIT %s
                """, (limit,))
                commits = cur.fetchall()

                print("="*60)
                print(f"GitHub 커밋 (최근 {limit}개)")
                print("="*60)
                print()

                for commit in commits:
                    print(f"[{commit['sha'][:8]}] {commit['repo']}")
                    print(f"   {commit['message'][:60]}")
                    print(f"   {commit['commit_date']} (+{commit['additions']} -{commit['deletions']})")
                    print()

            elif item_type == 'ai-chat':
                cur.execute("""
                    SELECT
                        id,
                        provider,
                        title,
                        created_at
                    FROM learning.ai_chat_conversations
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                conversations = cur.fetchall()

                print("="*60)
                print(f"AI 채팅 (최근 {limit}개)")
                print("="*60)
                print()

                for conv in conversations:
                    print(f"[{conv['provider']}] {conv['title'] or '(제목 없음)'}")
                    print(f"   ID: {conv['id']} | {conv['created_at']}")
                    print()

            elif item_type == 'baekjoon':
                cur.execute("""
                    SELECT
                        problem_number,
                        title,
                        tier,
                        language,
                        solved_date
                    FROM learning.baekjoon_solutions
                    ORDER BY solved_date DESC
                    LIMIT %s
                """, (limit,))
                problems = cur.fetchall()

                print("="*60)
                print(f"백준 풀이 (최근 {limit}개)")
                print("="*60)
                print()

                for problem in problems:
                    print(f"[{problem['problem_number']}] {problem['title']}")
                    print(f"   {problem['tier']} | {problem['language']} | {problem['solved_date']}")
                    print()

    def show_detail(self, item_type, item_id):
        """항목 상세"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            if item_type == 'ai-chat':
                cur.execute("""
                    SELECT
                        c.id,
                        c.provider,
                        c.title,
                        c.link,
                        c.user_messages,
                        c.assistant_messages,
                        c.has_code,
                        c.conversation_path,
                        c.code_languages,
                        c.created_at,
                        c.messages
                    FROM learning.ai_chat_conversations c
                    WHERE c.id = %s
                """, (item_id,))
                conv = cur.fetchone()

                if conv:
                    print("="*60)
                    print(f"AI Chat: [{conv['provider']}] {conv['title'] or '(제목 없음)'}")
                    print("="*60)
                    print()
                    print(f"ID: {conv['id']}")
                    print(f"Provider: {conv['provider']}")
                    if conv['link']:
                        print(f"Link: {conv['link']}")
                    print(f"메시지: 사용자 {conv['user_messages']}개, AI {conv['assistant_messages']}개")
                    if conv['has_code']:
                        print(f"코드: {', '.join(conv['code_languages']) if conv['code_languages'] else 'N/A'}")
                    print(f"날짜: {conv['created_at']}")
                    print()

                    # DB에서 messages 읽기 (우선), 없으면 JSON 파일에서 읽기
                    messages = None

                    if conv.get('messages'):
                        # DB에 messages가 있으면 사용
                        messages = conv['messages']
                        print("[DB에서 로드됨]")
                    elif conv['conversation_path']:
                        # DB에 없으면 JSON 파일에서 읽기
                        json_path = Path(conv['conversation_path'])
                        if json_path.exists():
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                messages = data.get('messages', [])
                            print("[파일에서 로드됨]")
                        else:
                            print(f"[WARNING] 대화 파일을 찾을 수 없습니다: {conv['conversation_path']}")

                    # 메시지 출력
                    if messages:
                        print("="*60)
                        print("대화 내용")
                        print("="*60)
                        print()

                        for i, msg in enumerate(messages, 1):
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '')

                            if role == 'user':
                                print(f"[사용자]")
                            else:
                                print(f"[{conv['provider'].title()}]")

                            print(content)
                            print()

                            if i < len(messages):
                                print("-" * 60)
                                print()
                    else:
                        print("[WARNING] 대화 내용을 찾을 수 없습니다.")
                else:
                    print(f"[ERROR] AI Chat을 찾을 수 없습니다: {item_id}")

            elif item_type == 'github':
                cur.execute("""
                    SELECT *
                    FROM learning.github_commits
                    WHERE sha = %s
                """, (item_id,))
                commit = cur.fetchone()

                if commit:
                    print("="*60)
                    print(f"GitHub 커밋: {commit['sha'][:8]}")
                    print("="*60)
                    print()
                    print(f"레포: {commit['repo']}")
                    print(f"메시지: {commit['message']}")
                    print(f"날짜: {commit['commit_date']}")
                    print(f"URL: {commit['url']}")
                    print(f"변경: +{commit['additions']} -{commit['deletions']} (~{commit['files_changed']} 파일)")
                    print()

                    if commit['files']:
                        print("파일 목록:")
                        files = json.loads(commit['files']) if isinstance(commit['files'], str) else commit['files']
                        for f in files:
                            print(f"  {f['status']:10} {f['filename']}")
                        print()
                else:
                    print(f"[ERROR] 커밋을 찾을 수 없습니다: {item_id}")

    def export_data(self, target_date=None, output_dir='exports'):
        """데이터 내보내기"""
        if target_date is None:
            target_date = date.today()

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        filename = output_path / f"learning_data_{target_date}.json"

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # GitHub
            cur.execute("""
                SELECT *
                FROM learning.github_commits
                WHERE DATE(commit_date) = %s
            """, (target_date,))
            github_commits = cur.fetchall()

            # AI Chat
            cur.execute("""
                SELECT *
                FROM learning.ai_chat_conversations
                WHERE DATE(created_at) = %s
            """, (target_date,))
            ai_chats = cur.fetchall()

            # Baekjoon
            cur.execute("""
                SELECT *
                FROM learning.baekjoon_solutions
                WHERE DATE(solved_date) = %s
            """, (target_date,))
            baekjoon_solutions = cur.fetchall()

        data = {
            'date': str(target_date),
            'exported_at': datetime.now().isoformat(),
            'github_commits': [dict(row) for row in github_commits],
            'ai_conversations': [dict(row) for row in ai_chats],
            'baekjoon_solutions': [dict(row) for row in baekjoon_solutions],
            'summary': {
                'github_count': len(github_commits),
                'ai_chat_count': len(ai_chats),
                'baekjoon_count': len(baekjoon_solutions),
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        print(f"[SUCCESS] 내보내기 완료: {filename}")
        print(f"   GitHub: {len(github_commits)}개")
        print(f"   AI Chat: {len(ai_chats)}개")
        print(f"   Baekjoon: {len(baekjoon_solutions)}개")


def main():
    parser = argparse.ArgumentParser(description='개인 학습 정보 수집 CLI')
    subparsers = parser.add_subparsers(dest='command', help='명령어')

    # stats
    subparsers.add_parser('stats', help='전체 통계')

    # list
    list_parser = subparsers.add_parser('list', help='항목 목록')
    list_parser.add_argument('type', choices=['github', 'ai-chat', 'baekjoon'])
    list_parser.add_argument('--limit', type=int, default=20, help='표시 개수')

    # show
    show_parser = subparsers.add_parser('show', help='항목 상세')
    show_parser.add_argument('type', choices=['github', 'ai-chat'])
    show_parser.add_argument('id', help='항목 ID')

    # export
    export_parser = subparsers.add_parser('export', help='데이터 내보내기')
    export_parser.add_argument('--date', type=str, help='날짜 (YYYY-MM-DD)')
    export_parser.add_argument('--output', type=str, default='exports', help='출력 폴더')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = LearningCLI()
    if not cli.connect():
        return

    try:
        if args.command == 'stats':
            cli.stats()
        elif args.command == 'list':
            cli.list_items(args.type, args.limit)
        elif args.command == 'show':
            cli.show_detail(args.type, args.id)
        elif args.command == 'export':
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date() if args.date else None
            cli.export_data(target_date, args.output)
    finally:
        cli.close()


if __name__ == '__main__':
    main()
