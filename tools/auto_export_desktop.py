#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desktop 자동 Claude Export

동작:
1. Playwright로 브라우저 열기
2. claude.ai 로그인 (쿠키 사용)
3. Settings → Privacy → Export 클릭
4. 다운로드 완료 대기
5. NAS 또는 로컬 디렉토리로 이동

설정:
- USE_NAS = True: Z:\learning-etl\claude-exports\에 저장
- USE_NAS = False: Downloads\claude-exports\에 저장 후 SCP
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
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

# 설정
USE_NAS = True  # True: NAS 직접 저장, False: 로컬 저장 후 전송

if USE_NAS:
    # NAS 경로 (Z: 드라이브)
    EXPORT_DIR = Path("Z:/learning-etl/claude-exports")
else:
    # 로컬 경로
    EXPORT_DIR = Path(os.path.expanduser("~/Downloads/claude-exports"))

# 크롬 기본 다운로드 경로
DOWNLOADS_DIR = Path(os.path.expanduser("~/Downloads"))


def ensure_export_dir():
    """Export 디렉토리 생성"""
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Export 디렉토리: {EXPORT_DIR}")
        return True
    except Exception as e:
        print(f"❌ 디렉토리 생성 실패: {e}")
        if USE_NAS:
            print("NAS(Z:)가 마운트되어 있는지 확인하세요.")
        return False


def auto_export_claude(headless=False):
    """Claude Export 자동 실행

    Args:
        headless: True면 백그라운드 실행

    Returns:
        다운로드된 파일 경로 또는 None
    """
    print("=" * 60)
    print("Claude.ai 자동 Export")
    print("=" * 60)
    print()

    # 쿠키 확인
    if not CLAUDE_COOKIES_PATH.exists():
        print(f"❌ 쿠키 파일이 없습니다: {CLAUDE_COOKIES_PATH}")
        print("먼저 쿠키를 추출하세요:")
        print("  python tools/extract_cookies_playwright.py")
        return None

    import json
    with open(CLAUDE_COOKIES_PATH, 'r') as f:
        cookies = json.load(f)

    print(f"✅ 쿠키 로드: {len(cookies)}개")
    print()

    with sync_playwright() as p:
        # 크롬 프로필 사용 (쿠키 자동 적용)
        print("🌐 브라우저 실행 중...")

        # 다운로드 경로 설정
        browser = p.chromium.launch(
            headless=headless,
            downloads_path=str(DOWNLOADS_DIR)
        )

        context = browser.new_context(
            accept_downloads=True
        )

        # 쿠키 추가
        context.add_cookies(cookies)

        page = context.new_page()

        try:
            # 1. claude.ai 접속
            print("📡 claude.ai 접속...")
            page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)

            # Cloudflare 체크
            try:
                page.wait_for_function(
                    "() => !document.querySelector('iframe[src*=\"challenges.cloudflare.com\"]')",
                    timeout=10000
                )
                print("✅ Cloudflare 통과")
            except:
                print("⚠️  Cloudflare 대기 타임아웃 (계속 진행)")

            # 2. Settings 페이지로 이동
            print("⚙️  Settings 페이지 이동...")
            page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)

            # Cloudflare 챌린지 대기 (Settings 페이지에서 또 나올 수 있음)
            print("⏳ Cloudflare 챌린지 확인 중...")

            # 반복적으로 Cloudflare 감지 및 대기 (최대 3번)
            for attempt in range(3):
                page.wait_for_timeout(2000)
                page_text = page.inner_text('body')

                # Cloudflare 페이지인지 확인
                is_cloudflare = (
                    '사람인지 확인' in page_text or
                    'Verifying' in page_text or
                    '확인 중' in page_text or
                    'challenges.cloudflare.com' in page.content() or
                    'Cloudflare' in page_text and len(page_text) < 500  # 짧은 페이지 = 챌린지
                )

                if is_cloudflare:
                    print(f"  [{attempt+1}/3] Cloudflare 감지 - 대기 중... (30초)")
                    try:
                        # Cloudflare가 사라질 때까지 대기
                        page.wait_for_function(
                            """() => {
                                const text = document.body.innerText;
                                const html = document.body.innerHTML;
                                return !text.includes('사람인지 확인') &&
                                       !text.includes('Verifying') &&
                                       !text.includes('확인 중') &&
                                       !html.includes('challenges.cloudflare.com') &&
                                       text.length > 500;
                            }""",
                            timeout=30000
                        )
                        print("  ✅ Cloudflare 통과")
                        break
                    except:
                        if attempt == 2:
                            print("  ⚠️  Cloudflare 타임아웃 - 스크린샷 저장")
                            cf_fail = PROJECT_ROOT / 'temp' / 'cloudflare_failed.png'
                            page.screenshot(path=str(cf_fail))
                            print(f"  📸 {cf_fail}")
                        continue
                else:
                    print("✅ Cloudflare 없음 (Settings 정상)")
                    break

            page.wait_for_timeout(2000)

            # 3. Privacy 탭 찾기 (여러 셀렉터 시도)
            print("🔐 Privacy 탭 찾기...")
            privacy_selectors = [
                "a:has-text('Privacy')",
                "a:has-text('개인정보보호')",
                "a[href*='privacy']",
                "button:has-text('Privacy')",
                "[role='tab']:has-text('Privacy')"
            ]

            privacy_clicked = False
            for selector in privacy_selectors:
                try:
                    privacy_link = page.locator(selector).first
                    privacy_link.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    print(f"✅ Privacy 탭 클릭: {selector}")
                    privacy_clicked = True
                    break
                except:
                    continue

            if not privacy_clicked:
                # 스크린샷 저장
                debug_ss = PROJECT_ROOT / 'temp' / 'export_debug.png'
                page.screenshot(path=str(debug_ss))
                print(f"⚠️  Privacy 탭을 찾을 수 없습니다. 스크린샷: {debug_ss}")

            # 4. Export 버튼 클릭 및 다운로드
            print("💾 Export 버튼 클릭...")
            export_selectors = [
                "button:has-text('Export data')",
                "button:has-text('데이터 내보내기')",
                "button:has-text('Export')",
                "button:has-text('내보내기')",
                "a:has-text('Export')"
            ]

            downloaded_file = None

            with page.expect_download(timeout=120000) as download_info:
                export_clicked = False
                for selector in export_selectors:
                    try:
                        export_btn = page.locator(selector).first
                        export_btn.click(timeout=5000)
                        print(f"✅ Export 버튼 클릭: {selector}")
                        export_clicked = True
                        break
                    except:
                        continue

                if not export_clicked:
                    raise Exception("Export 버튼을 찾을 수 없습니다")

            # 다운로드 완료 대기
            download = download_info.value
            print("⏳ 다운로드 중...")

            # 임시 경로에 저장
            temp_path = DOWNLOADS_DIR / download.suggested_filename
            download.save_as(temp_path)

            print(f"✅ 다운로드 완료: {temp_path.name}")

            # 목적지로 이동
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            final_filename = f"claude_export_{timestamp}.zip"
            final_path = EXPORT_DIR / final_filename

            shutil.move(str(temp_path), str(final_path))
            print(f"📦 저장 완료: {final_path}")

            downloaded_file = str(final_path)

        except Exception as e:
            print(f"❌ Export 실패: {e}")
            import traceback
            traceback.print_exc()
            downloaded_file = None

        finally:
            browser.close()

    return downloaded_file


def main():
    """메인 함수"""
    print("=" * 60)
    print("Desktop 자동 Claude Export")
    print(f"모드: {'NAS 직접 저장' if USE_NAS else '로컬 저장 후 전송'}")
    print("=" * 60)
    print()

    # Export 디렉토리 확인
    if not ensure_export_dir():
        return

    # Export 실행
    result_file = auto_export_claude(headless=False)

    if result_file:
        print()
        print("=" * 60)
        print("✅ Export 성공!")
        print(f"📁 파일: {result_file}")
        print("=" * 60)

        if USE_NAS:
            print()
            print("다음 단계:")
            print("  - Pi가 자동으로 파일을 감지하고 파싱합니다")
            print("  - 별도 작업 필요 없음")
        else:
            print()
            print("다음 단계:")
            print(f"  1. Pi로 전송: scp {result_file} pi:~/learning-etl/temp/")
            print(f"  2. Pi에서 파싱: python parse/claude_parse.py")
    else:
        print()
        print("❌ Export 실패")


if __name__ == '__main__':
    # 인자로 headless 모드 지원
    import sys
    headless = '--headless' in sys.argv

    if headless:
        print("(Headless 모드)")

    main()
