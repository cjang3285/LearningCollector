#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Export UI 디버깅 도구

Playwright로 Settings 페이지 접근 시 UI 요소를 찾지 못하는 문제 분석

실행:
  python tools/debug_export_ui.py
"""

import os
import sys
import time
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


def debug_ui():
    """UI 요소 디버깅"""
    print("=" * 60)
    print("Claude Export UI 디버깅")
    print("=" * 60)
    print()

    # 쿠키 확인
    if not CLAUDE_COOKIES_PATH.exists():
        print(f"❌ 쿠키 파일이 없습니다: {CLAUDE_COOKIES_PATH}")
        return

    import json
    with open(CLAUDE_COOKIES_PATH, 'r') as f:
        cookies = json.load(f)

    print(f"✅ 쿠키 로드: {len(cookies)}개")
    print()

    with sync_playwright() as p:
        print("🌐 브라우저 실행...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            # Step 1: 홈페이지 접속
            print()
            print("[Step 1] claude.ai 홈페이지 접속")
            print("-" * 60)
            page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)

            # Cloudflare 대기
            print("⏳ Cloudflare 체크 중...")
            try:
                page.wait_for_function(
                    "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
                    timeout=15000
                )
                print("✅ Cloudflare 통과")
            except:
                print("⚠️  Cloudflare 타임아웃 (계속 진행)")

            time.sleep(3)

            # 현재 페이지 URL 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # HTML 일부 저장
            html_sample = page.content()[:500]
            print(f"📄 HTML 샘플:\n{html_sample}\n")

            # Step 2: Settings 페이지 이동
            print()
            print("[Step 2] Settings 페이지 이동")
            print("-" * 60)
            print("🔗 https://claude.ai/settings 이동 중...")

            page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)

            # Cloudflare 체크 (다시!)
            print("⏳ Cloudflare 체크 중...")
            cloudflare_detected = False
            try:
                # Cloudflare iframe 감지
                cf_iframe = page.locator('iframe[src*="challenges.cloudflare.com"]')
                if cf_iframe.count() > 0:
                    print("⚠️  Cloudflare 챌린지 감지!")
                    cloudflare_detected = True

                    # 스크린샷 저장
                    cf_screenshot = PROJECT_ROOT / 'temp' / 'cloudflare_challenge.png'
                    page.screenshot(path=str(cf_screenshot))
                    print(f"📸 스크린샷 저장: {cf_screenshot}")

                    # 수동 해결 대기
                    print()
                    print("=" * 60)
                    print("⚠️  Cloudflare 챌린지 수동 해결 필요")
                    print("=" * 60)
                    print("1. 브라우저 창에서 '사람인지 확인' 체크박스 클릭")
                    print("2. 챌린지 통과 후 아무 키나 누르세요...")
                    input()

                    # 재확인
                    page.wait_for_function(
                        "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
                        timeout=5000
                    )
                    print("✅ Cloudflare 통과 확인")
                else:
                    print("✅ Cloudflare 없음")
            except Exception as e:
                print(f"⚠️  Cloudflare 체크 에러: {e}")

            time.sleep(2)

            # 현재 URL 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # HTML 전체 덤프
            print()
            print("[Step 3] HTML 구조 분석")
            print("-" * 60)

            html_file = PROJECT_ROOT / 'temp' / 'settings_page.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page.content())
            print(f"💾 HTML 저장: {html_file}")

            # 페이지 텍스트 내용 확인
            page_text = page.inner_text('body')
            print(f"📝 페이지 텍스트 샘플 (처음 500자):")
            print(page_text[:500])
            print()

            # Privacy 텍스트 검색
            if 'Privacy' in page_text or '개인정보' in page_text or '프라이버시' in page_text:
                print("✅ 'Privacy' 또는 '개인정보' 텍스트 발견!")
            else:
                print("❌ 'Privacy' 텍스트 없음")

            # Export 텍스트 검색
            if 'Export' in page_text or '내보내기' in page_text or '데이터' in page_text:
                print("✅ 'Export' 또는 '내보내기' 텍스트 발견!")
            else:
                print("❌ 'Export' 텍스트 없음")

            print()
            print("[Step 4] 셀렉터 테스트")
            print("-" * 60)

            # Privacy 셀렉터 시도
            privacy_selectors = [
                "a:has-text('Privacy')",
                "a:has-text('개인정보보호')",
                "a:has-text('개인정보')",
                "a:has-text('프라이버시')",
                "a[href*='privacy']",
                "button:has-text('Privacy')",
                "[role='tab']:has-text('Privacy')",
                "nav a:has-text('Privacy')",
            ]

            privacy_found = None
            for selector in privacy_selectors:
                try:
                    element = page.locator(selector).first
                    count = element.count()
                    if count > 0:
                        print(f"✅ [{selector}] → {count}개 발견")
                        if not privacy_found:
                            privacy_found = selector
                            # 요소 정보 출력
                            print(f"   텍스트: {element.inner_text()}")
                            print(f"   href: {element.get_attribute('href')}")
                    else:
                        print(f"❌ [{selector}] → 없음")
                except Exception as e:
                    print(f"❌ [{selector}] → 에러: {e}")

            print()

            # Export 셀렉터 시도
            export_selectors = [
                "button:has-text('Export data')",
                "button:has-text('Export')",
                "button:has-text('내보내기')",
                "button:has-text('데이터 내보내기')",
                "a:has-text('Export')",
            ]

            export_found = None
            for selector in export_selectors:
                try:
                    element = page.locator(selector).first
                    count = element.count()
                    if count > 0:
                        print(f"✅ [{selector}] → {count}개 발견")
                        if not export_found:
                            export_found = selector
                            print(f"   텍스트: {element.inner_text()}")
                    else:
                        print(f"❌ [{selector}] → 없음")
                except Exception as e:
                    print(f"❌ [{selector}] → 에러: {e}")

            # 스크린샷 저장
            print()
            final_screenshot = PROJECT_ROOT / 'temp' / 'settings_final.png'
            page.screenshot(path=str(final_screenshot), full_page=True)
            print(f"📸 최종 스크린샷: {final_screenshot}")

            # 결과 요약
            print()
            print("=" * 60)
            print("디버깅 결과 요약")
            print("=" * 60)
            print(f"Privacy 셀렉터 발견: {privacy_found if privacy_found else '❌ 없음'}")
            print(f"Export 셀렉터 발견: {export_found if export_found else '❌ 없음'}")
            print()
            print("다음 파일 확인:")
            print(f"  - HTML: {html_file}")
            print(f"  - 스크린샷: {final_screenshot}")

            # 인터랙티브 모드
            print()
            print("=" * 60)
            print("인터랙티브 모드")
            print("=" * 60)
            print("브라우저 창이 열려있습니다.")
            print("수동으로 Privacy → Export 경로를 확인하고")
            print("개발자 도구로 정확한 셀렉터를 찾아보세요.")
            print()
            print("종료하려면 Enter를 누르세요...")
            input()

        except Exception as e:
            print(f"❌ 에러: {e}")
            import traceback
            traceback.print_exc()

            # 에러 스크린샷
            error_screenshot = PROJECT_ROOT / 'temp' / 'error_screenshot.png'
            page.screenshot(path=str(error_screenshot))
            print(f"📸 에러 스크린샷: {error_screenshot}")

        finally:
            browser.close()


if __name__ == '__main__':
    debug_ui()
