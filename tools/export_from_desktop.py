#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데스크톱에서 Claude Export를 실행하고 Pi로 전송

WireGuard VPN으로 연결되어 있으면 안전하게 전송 가능
"""

import sys
import subprocess
from pathlib import Path

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from export.claude_export import ClaudeExporter

def main():
    print("=" * 60)
    print("데스크톱에서 Claude Export 실행")
    print("=" * 60)
    print()

    # 데스크톱에서 Export 실행 (GUI 모드)
    exporter = ClaudeExporter(headless=False)
    zip_path = exporter.export()

    if not zip_path:
        print("❌ Export 실패")
        return

    print(f"✅ Export 완료: {zip_path}")
    print()

    # Pi로 전송
    pi_user = "jcw"
    pi_host = "183.101.163.146"
    pi_path = f"{pi_user}@{pi_host}:~/learning-etl/temp/claude_downloads/"

    print(f"🚀 Pi로 전송 중: {pi_path}")

    try:
        result = subprocess.run(
            ['scp', zip_path, pi_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ 전송 완료!")
            print()
            print(f"Pi에서 확인:")
            print(f"  ssh {pi_user}@{pi_host}")
            print(f"  ls -lh ~/learning-etl/temp/claude_downloads/")
        else:
            print(f"❌ 전송 실패: {result.stderr}")

    except Exception as e:
        print(f"❌ 전송 에러: {e}")

if __name__ == '__main__':
    main()
