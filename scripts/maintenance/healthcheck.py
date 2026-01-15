#!/usr/bin/env python3
"""
LearningCollector 헬스 체크 스크립트

- GitHub API Rate Limit 확인
- DB 연결 확인
- 최근 수집 상태 확인
- 디스크 공간 확인

텔레그램 알림 (선택):
    export TELEGRAM_BOT_TOKEN="your_token"
    export TELEGRAM_CHAT_ID="your_chat_id"
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
import psycopg2
from datetime import datetime, timedelta
from config.settings import (
    GITHUB_TOKEN, GITHUB_USERNAME,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
)

# 텔레그램 설정 (선택)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_telegram(message):
    """텔레그램 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")


def check_github_api():
    """GitHub API Rate Limit 확인"""
    print("1️⃣ GitHub API 확인...")

    try:
        headers = {
            'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json'
        }
        response = requests.get('https://api.github.com/rate_limit', headers=headers, timeout=5)
        response.raise_for_status()

        data = response.json()
        core = data['rate']
        remaining = core['remaining']
        limit = core['limit']
        reset_time = datetime.fromtimestamp(core['reset'])

        print(f"  ✅ GitHub API 연결 성공")
        print(f"     남은 호출: {remaining}/{limit}")
        print(f"     리셋 시간: {reset_time}")

        # 경고
        if remaining < 100:
            warning = f"⚠️ GitHub API Rate Limit 부족: {remaining}/{limit}"
            print(f"  {warning}")
            send_telegram(warning)

        return True
    except Exception as e:
        error = f"❌ GitHub API 연결 실패: {e}"
        print(f"  {error}")
        send_telegram(error)
        return False


def check_database():
    """데이터베이스 연결 및 상태 확인"""
    print("\n2️⃣ 데이터베이스 확인...")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        print(f"  ✅ 데이터베이스 연결 성공")

        # 최근 수집 확인
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    artifact_type,
                    MAX(artifact_date) as last_date,
                    COUNT(*) as count
                FROM learning.learning_artifacts
                WHERE artifact_date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY artifact_type
            """)
            recent = cur.fetchall()

            print("     최근 7일 수집:")
            for row in recent:
                print(f"       {row[0]:15} {row[2]:3}개 (최근: {row[1]})")

            # 오늘 수집 확인
            cur.execute("""
                SELECT artifact_type, COUNT(*)
                FROM learning.learning_artifacts
                WHERE artifact_date = CURRENT_DATE
                GROUP BY artifact_type
            """)
            today = cur.fetchall()

            if today:
                print("     오늘 수집:")
                for row in today:
                    print(f"       {row[0]:15} {row[1]:3}개")
            else:
                warning = "⚠️ 오늘 수집된 데이터 없음"
                print(f"  {warning}")
                # 오늘 데이터 없어도 알림은 안 보냄 (cron 전이면 정상)

        conn.close()
        return True
    except Exception as e:
        error = f"❌ 데이터베이스 연결 실패: {e}"
        print(f"  {error}")
        send_telegram(error)
        return False


def check_disk_space():
    """디스크 공간 확인"""
    print("\n3️⃣ 디스크 공간 확인...")

    try:
        import shutil
        total, used, free = shutil.disk_usage("/")

        total_gb = total // (2**30)
        used_gb = used // (2**30)
        free_gb = free // (2**30)
        percent = (used / total) * 100

        print(f"  ✅ 디스크 공간")
        print(f"     전체: {total_gb}GB")
        print(f"     사용: {used_gb}GB ({percent:.1f}%)")
        print(f"     여유: {free_gb}GB")

        # 경고
        if free_gb < 5:
            warning = f"⚠️ 디스크 공간 부족: {free_gb}GB 남음"
            print(f"  {warning}")
            send_telegram(warning)

        return True
    except Exception as e:
        print(f"  ❌ 디스크 확인 실패: {e}")
        return False


def check_logs():
    """로그 파일 확인"""
    print("\n4️⃣ 로그 파일 확인...")

    log_dir = PROJECT_ROOT / "logs"
    if not log_dir.exists():
        print("  ⏭️  logs 폴더 없음")
        return True

    # 로그 파일 크기
    total_size = sum(f.stat().st_size for f in log_dir.glob("*.log"))
    total_mb = total_size / (1024 * 1024)

    print(f"  ✅ 로그 파일")
    print(f"     총 크기: {total_mb:.1f}MB")
    print(f"     파일 수: {len(list(log_dir.glob('*.log')))}개")

    # 최근 에러 확인
    today_log = log_dir / f"main_{datetime.now().strftime('%Y%m%d')}.log"
    if today_log.exists():
        with open(today_log, 'r') as f:
            content = f.read()
            error_count = content.count('ERROR')
            if error_count > 0:
                warning = f"⚠️ 오늘 로그에 ERROR {error_count}개 발견"
                print(f"  {warning}")

    return True


def main():
    print("="*60)
    print("🏥 LearningCollector 헬스 체크")
    print("="*60)
    print(f"시간: {datetime.now()}")
    print()

    results = []

    results.append(check_github_api())
    results.append(check_database())
    results.append(check_disk_space())
    results.append(check_logs())

    print()
    print("="*60)

    if all(results):
        print("✅ 모든 체크 통과")
        print("="*60)
        return 0
    else:
        print("⚠️ 일부 체크 실패")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
