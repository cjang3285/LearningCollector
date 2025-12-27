#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude.ai 대화 Export (비공식 API 라이브러리 사용)

claude-api-py를 사용하여 모든 대화를 가져옵니다.
Desktop과 Pi 모두에서 실행 가능 (Cloudflare 우회)

설치: pip install claude-api-py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CLAUDE_COOKIES_PATH, CLAUDE_DOWNLOAD_DIR

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def extract_session_key(cookies_path: Path = CLAUDE_COOKIES_PATH) -> Optional[str]:
    """쿠키 파일에서 sessionKey 추출

    claude-api-py는 브라우저 쿠키의 sessionKey를 사용합니다.
    sessionKey는 sk-ant-sid01로 시작하는 값입니다.

    Args:
        cookies_path: 쿠키 JSON 파일 경로

    Returns:
        sessionKey 값 또는 None
    """
    if not cookies_path.exists():
        print(f"❌ 쿠키 파일이 없습니다: {cookies_path}")
        print("먼저 쿠키를 추출하세요:")
        print("  python tools/extract_cookies_playwright.py")
        return None

    with open(cookies_path, 'r') as f:
        cookies = json.load(f)

    # sessionKey 찾기 (sk-ant-sid01... 형태)
    for cookie in cookies:
        if cookie['name'] == 'sessionKey':
            return cookie['value']

    # sessionKey가 없으면 다른 쿠키들도 확인
    print("⚠️  sessionKey 쿠키를 찾을 수 없습니다.")
    print()
    print("발견된 쿠키:")
    for cookie in cookies:
        print(f"  - {cookie['name']}")
    print()
    print("sessionKey는 브라우저 개발자 도구에서 직접 복사해야 할 수 있습니다:")
    print("  1. Chrome에서 claude.ai 로그인")
    print("  2. F12 → Application → Cookies → claude.ai")
    print("  3. 'sessionKey' 필드 복사 (sk-ant-sid01...로 시작)")

    return None


def export_with_library(session_key: str, output_dir: Path = None):
    """claude-api-py 라이브러리로 대화 Export

    Args:
        session_key: sessionKey 값 (sk-ant-sid01...)
        output_dir: 저장 디렉토리 (기본: CLAUDE_DOWNLOAD_DIR)
    """
    if output_dir is None:
        output_dir = CLAUDE_DOWNLOAD_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Claude.ai 전체 대화 Export (claude-api-py)")
    print("=" * 60)
    print()

    try:
        from claude_api import client as claude_client

        # 클라이언트 초기화
        print("📡 Claude API 클라이언트 초기화...")
        claude = claude_client.ClaudeClient(session_key)

        # 조직 정보 가져오기
        print("🏢 조직 정보 가져오기...")
        orgs = claude.get_organizations()
        print(f"✅ {len(orgs)}개 조직 발견")

        if not orgs:
            print("❌ 조직을 찾을 수 없습니다")
            return None

        # 첫 번째 조직 사용
        org_id = orgs[0]['uuid']
        print(f"   조직 ID: {org_id}")
        print()

        # 대화 목록 가져오기
        print("📋 대화 목록 가져오기...")
        conversations = claude.get_conversations()
        print(f"✅ {len(conversations)}개 대화 발견")
        print()

        if not conversations:
            print("⚠️  대화가 없습니다.")
            return None

        # 각 대화 상세 정보 가져오기
        full_conversations = []

        for i, conv in enumerate(conversations, 1):
            conv_id = conv['uuid']
            conv_name = conv.get('name', 'Untitled')

            print(f"[{i}/{len(conversations)}] {conv_name[:50]}...")

            try:
                # 대화 상세 정보
                conv_info = claude.get_conversation_info(conversation_uuid=conv_id)
                full_conversations.append(conv_info)
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                continue

        # JSON으로 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'claude_conversations_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'organization_id': org_id,
                'total_conversations': len(full_conversations),
                'conversations': full_conversations
            }, f, indent=2, ensure_ascii=False)

        print()
        print("=" * 60)
        print(f"✅ Export 완료!")
        print(f"💾 파일: {output_file}")
        print(f"📊 대화 수: {len(full_conversations)}")
        print(f"📦 크기: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
        print("=" * 60)

        return str(output_file)

    except ImportError:
        print("❌ claude-api-py 라이브러리가 설치되지 않았습니다.")
        print()
        print("설치 명령:")
        print("  pip install claude-api-py")
        return None

    except Exception as e:
        print(f"❌ Export 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 함수"""
    print("=" * 60)
    print("Claude.ai 대화 Export (비공식 API)")
    print("=" * 60)
    print()

    # 1. sessionKey 추출
    session_key = extract_session_key()

    if not session_key:
        print()
        print("수동으로 sessionKey를 입력하시겠습니까? (Enter로 스킵)")
        manual_key = input("sessionKey (sk-ant-sid01...): ").strip()

        if manual_key:
            session_key = manual_key
        else:
            print("❌ sessionKey가 없어 종료합니다.")
            return

    print(f"✅ sessionKey: {session_key[:30]}...")
    print()

    # 2. Export 실행
    output_file = export_with_library(session_key)

    if output_file:
        print()
        print("다음 단계:")
        print(f"  1. Pi로 전송: scp {output_file} pi:~/learning-etl/temp/")
        print(f"  2. Pi에서 파싱: python parse/claude_parse.py")


if __name__ == '__main__':
    main()
