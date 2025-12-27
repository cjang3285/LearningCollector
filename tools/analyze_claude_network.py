#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude.ai 네트워크 요청 분석

브라우저에서 Export 버튼 클릭 시 발생하는 API 호출을 캡처합니다.
목표: Export API 엔드포인트와 필요한 헤더/쿠키 파악
"""

import os
import sys
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CLAUDE_COOKIES_PATH

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def analyze_network_requests():
    """네트워크 요청 분석"""

    print("=" * 60)
    print("Claude.ai 네트워크 요청 분석")
    print("=" * 60)
    print()

    # 쿠키 로드
    if not CLAUDE_COOKIES_PATH.exists():
        print(f"❌ 쿠키 파일이 없습니다: {CLAUDE_COOKIES_PATH}")
        print("먼저 쿠키를 추출하세요:")
        print("  python tools/extract_cookies_playwright.py")
        return

    with open(CLAUDE_COOKIES_PATH, 'r') as f:
        cookies = json.load(f)

    print(f"✅ 쿠키 로드: {len(cookies)}개")

    # sessionKey 추출
    session_key = None
    for cookie in cookies:
        if cookie['name'] == 'sessionKey':
            session_key = cookie['value']
            break

    if session_key:
        print(f"✅ sessionKey 발견: {session_key[:20]}...")
    else:
        print("⚠️  sessionKey를 찾을 수 없습니다")

    print()

    # 네트워크 요청 캡처
    captured_requests = []

    def handle_request(request):
        """모든 네트워크 요청 캡처"""
        url = request.url
        method = request.method
        headers = request.headers

        # claude.ai API 호출만 기록
        if 'claude.ai' in url or 'anthropic' in url:
            captured_requests.append({
                'url': url,
                'method': method,
                'headers': headers,
                'resource_type': request.resource_type
            })

            print(f"📡 {method} {url}")

            # Export 관련 요청 상세 출력
            if 'export' in url.lower() or 'download' in url.lower():
                print(f"   🎯 Export 관련 요청 발견!")
                print(f"   Headers: {json.dumps(headers, indent=2)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # 쿠키 추가
        context.add_cookies(cookies)

        page = context.new_page()

        # 네트워크 요청 이벤트 리스너
        page.on('request', handle_request)

        print("브라우저 실행됨. 수동으로 다음 작업을 수행하세요:")
        print("1. claude.ai 접속")
        print("2. Settings → Privacy → Export data 클릭")
        print("3. Export 완료될 때까지 대기")
        print()
        print("Enter를 누르면 분석을 종료합니다...")
        print()

        # claude.ai로 이동
        page.goto("https://claude.ai")
        page.wait_for_timeout(5000)

        # 사용자 입력 대기
        input()

        browser.close()

    # 결과 저장
    result_file = PROJECT_ROOT / 'temp' / 'claude_network_analysis.json'
    result_file.parent.mkdir(parents=True, exist_ok=True)

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"총 {len(captured_requests)}개 요청 캡처")
    print(f"결과 저장: {result_file}")
    print("=" * 60)

    # Export 관련 요청만 필터링
    export_requests = [r for r in captured_requests if 'export' in r['url'].lower() or 'download' in r['url'].lower()]

    if export_requests:
        print()
        print("🎯 Export 관련 요청:")
        for req in export_requests:
            print(f"  {req['method']} {req['url']}")
    else:
        print()
        print("⚠️  Export 관련 요청을 찾지 못했습니다.")
        print("수동으로 Export를 클릭했는지 확인하세요.")


if __name__ == '__main__':
    analyze_network_requests()
