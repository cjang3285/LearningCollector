#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude.ai 직접 API 호출 (Export 우회)

Playwright Export 대신 sessionKey로 직접 API를 호출하여
모든 대화를 가져옵니다. Cloudflare 우회 가능.

참고: st1vms/unofficial-claude-api 분석 결과 기반
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

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


class ClaudeAPIClient:
    """Claude.ai 직접 API 클라이언트"""

    BASE_URL = "https://claude.ai/api"

    def __init__(self, cookies_path: Path = CLAUDE_COOKIES_PATH):
        """
        Args:
            cookies_path: 쿠키 JSON 파일 경로
        """
        self.session = requests.Session()

        # 쿠키 로드
        with open(cookies_path, 'r') as f:
            cookies_list = json.load(f)

        # 쿠키를 requests session에 추가
        for cookie in cookies_list:
            self.session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie.get('domain', 'claude.ai'),
                path=cookie.get('path', '/')
            )

        # 기본 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://claude.ai',
            'Referer': 'https://claude.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })

        self.organization_id = None

    def get_organizations(self) -> List[Dict]:
        """조직 정보 가져오기"""
        url = f"{self.BASE_URL}/organizations"

        print(f"📡 GET {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        orgs = response.json()
        print(f"✅ {len(orgs)}개 조직 발견")

        return orgs

    def get_organization_id(self) -> str:
        """조직 ID 가져오기 (자동)"""
        if self.organization_id:
            return self.organization_id

        orgs = self.get_organizations()
        if not orgs:
            raise ValueError("조직을 찾을 수 없습니다")

        # 첫 번째 조직 사용
        self.organization_id = orgs[0]['uuid']
        print(f"🏢 조직 ID: {self.organization_id}")

        return self.organization_id

    def list_conversations(self, limit: int = 100) -> List[Dict]:
        """모든 대화 목록 가져오기

        Args:
            limit: 가져올 대화 수 (기본 100개)

        Returns:
            대화 목록 [{'uuid': ..., 'name': ..., 'updated_at': ...}, ...]
        """
        org_id = self.get_organization_id()
        url = f"{self.BASE_URL}/organizations/{org_id}/chat_conversations"

        print(f"📡 GET {url} (limit={limit})")
        response = self.session.get(url, params={'limit': limit}, timeout=30)
        response.raise_for_status()

        conversations = response.json()
        print(f"✅ {len(conversations)}개 대화 발견")

        return conversations

    def get_conversation(self, conversation_id: str) -> Dict:
        """특정 대화 내용 가져오기

        Args:
            conversation_id: 대화 UUID

        Returns:
            대화 전체 정보 {'uuid': ..., 'name': ..., 'chat_messages': [...]}
        """
        org_id = self.get_organization_id()
        url = f"{self.BASE_URL}/organizations/{org_id}/chat_conversations/{conversation_id}"

        print(f"📡 GET {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        conversation = response.json()
        message_count = len(conversation.get('chat_messages', []))
        print(f"✅ {message_count}개 메시지")

        return conversation

    def export_all_conversations(self, output_dir: Path = None) -> str:
        """모든 대화를 JSON으로 내보내기

        Args:
            output_dir: 저장할 디렉토리 (기본: CLAUDE_DOWNLOAD_DIR)

        Returns:
            저장된 파일 경로
        """
        if output_dir is None:
            output_dir = CLAUDE_DOWNLOAD_DIR

        output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("Claude.ai 전체 대화 Export (직접 API)")
        print("=" * 60)
        print()

        # 1. 대화 목록 가져오기
        conversations = self.list_conversations(limit=1000)

        if not conversations:
            print("⚠️  대화가 없습니다.")
            return None

        # 2. 각 대화 상세 내용 가져오기
        full_conversations = []

        for i, conv_summary in enumerate(conversations, 1):
            conv_id = conv_summary['uuid']
            conv_name = conv_summary.get('name', 'Untitled')

            print(f"[{i}/{len(conversations)}] {conv_name[:50]}...")

            try:
                full_conv = self.get_conversation(conv_id)
                full_conversations.append(full_conv)
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                continue

        # 3. JSON으로 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'claude_conversations_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_conversations': len(full_conversations),
                'conversations': full_conversations
            }, f, indent=2, ensure_ascii=False)

        print()
        print("=" * 60)
        print(f"✅ Export 완료!")
        print(f"💾 파일: {output_file}")
        print(f"📊 대화 수: {len(full_conversations)}")
        print(f"📦 크기: {output_file.stat().st_size / 1024:.1f} KB")
        print("=" * 60)

        return str(output_file)


def extract_session_key(cookies_path: Path = CLAUDE_COOKIES_PATH) -> Optional[str]:
    """쿠키 파일에서 sessionKey 추출

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

    # sessionKey 또는 activitySessionId 찾기
    for cookie in cookies:
        if cookie['name'] in ['sessionKey', 'activitySessionId']:
            print(f"✅ {cookie['name']} 발견")
            return cookie['value']

    print("❌ sessionKey 또는 activitySessionId를 찾을 수 없습니다")
    return None


def main():
    """메인 함수"""
    print("=" * 60)
    print("Claude.ai 직접 API Export")
    print("=" * 60)
    print()

    # 1. 쿠키 확인
    if not CLAUDE_COOKIES_PATH.exists():
        print(f"❌ 쿠키 파일이 없습니다: {CLAUDE_COOKIES_PATH}")
        print("먼저 쿠키를 추출하세요:")
        print("  python tools/extract_cookies_playwright.py")
        return

    # sessionKey 존재 확인 (선택)
    session_key = extract_session_key()
    if session_key:
        print(f"   Value: {session_key[:30]}...")
    print()

    # 2. API 클라이언트 생성
    client = ClaudeAPIClient(CLAUDE_COOKIES_PATH)

    # 3. 전체 대화 Export
    try:
        output_file = client.export_all_conversations()

        if output_file:
            print()
            print("다음 단계:")
            print(f"  1. Pi로 전송: scp {output_file} pi:~/learning-etl/temp/")
            print(f"  2. Pi에서 파싱: python parse/claude_parse.py {output_file}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ API 에러: {e}")
        print(f"   응답: {e.response.text if e.response else 'N/A'}")
        print()
        print("가능한 원인:")
        print("  - sessionKey가 만료됨")
        print("  - Claude.ai API 변경")
        print("  - 네트워크 문제")
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
