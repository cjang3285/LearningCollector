#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Export (수동 Cloudflare 해결)

Playwright로 브라우저를 열고, 사용자가 Cloudflare 체크박스를 클릭한 후
자동으로 Export를 진행합니다.

실행:
  python tools/auto_export_manual.py
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
USE_NAS = True

if USE_NAS:
    EXPORT_DIR = Path("Z:/learning-etl/claude-exports")
else:
    EXPORT_DIR = Path(os.path.expanduser("~/Downloads/claude-exports"))

DOWNLOADS_DIR = Path(os.path.expanduser("~/Downloads"))


def ensure_export_dir():
    """Export 디렉토리 생성"""
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Export 디렉토리: {EXPORT_DIR}")
        return True
    except Exception as e:
        print(f"❌ 디렉토리 생성 실패: {e}")
        return False


def auto_export_manual():
    """수동 Cloudflare 해결 후 자동 Export"""
    print("=" * 60)
    print("Claude.ai Export (수동 Cloudflare 해결)")
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
        print("🌐 브라우저 실행...")
        browser = p.chromium.launch(
            headless=False,
            downloads_path=str(DOWNLOADS_DIR)
        )

        context = browser.new_context(accept_downloads=True)
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            # 1. claude.ai 접속
            print("📡 claude.ai 접속...")
            page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)

            # 2. Settings 페이지로 이동
            print("⚙️  Settings 페이지 이동...")
            try:
                page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                if 'challenge_redirect' in str(e):
                    print("   리다이렉트 감지 - 재시도...")
                    time.sleep(3)
                    page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)
                else:
                    raise

            time.sleep(3)

            # 3. Cloudflare 체크
            page_text = page.inner_text('body')
            if '사람인지 확인' in page_text or ('Cloudflare' in page_text and len(page_text) < 1000):
                print()
                print("=" * 60)
                print("⚠️  Cloudflare 챌린지 감지")
                print("=" * 60)
                print("브라우저 창에서 '사람인지 확인' 체크박스를 클릭하세요.")
                print("완료되면 자동으로 다음 단계로 진행됩니다...")
                print("(최대 5분 대기)")
                print()

                # 사용자가 해결할 때까지 대기
                page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        return !text.includes('사람인지 확인') &&
                               text.length > 1000;
                    }""",
                    timeout=300000  # 5분
                )
                print("✅ Cloudflare 통과!")
                time.sleep(2)

            # 4. Privacy 탭 찾기
            print("🔐 Privacy 탭 찾기...")
            privacy_selectors = [
                "a:has-text('Privacy')",
                "a:has-text('개인정보')",
                "a[href*='privacy']",
            ]

            privacy_clicked = False
            for selector in privacy_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        element.click(timeout=5000)
                        time.sleep(2)
                        print(f"✅ Privacy 탭 클릭: {selector}")
                        privacy_clicked = True
                        break
                except:
                    continue

            if not privacy_clicked:
                # 페이지에 Privacy가 있는지 확인
                current_text = page.inner_text('body')
                if 'Privacy' not in current_text and '개인정보' not in current_text:
                    debug_ss = PROJECT_ROOT / 'temp' / 'no_privacy.png'
                    page.screenshot(path=str(debug_ss), full_page=True)
                    print(f"❌ Privacy 탭을 찾을 수 없습니다: {debug_ss}")
                    raise Exception("Privacy 탭 없음")
                else:
                    print("✅ Privacy 섹션 확인")

            # 5. Export 버튼 클릭 및 다운로드
            print("💾 Export 버튼 찾기...")
            export_selectors = [
                "button:has-text('Export data')",
                "button:has-text('Export')",
                "button:has-text('내보내기')",
                "button:has-text('데이터 내보내기')",
            ]

            downloaded_file = None

            with page.expect_download(timeout=180000) as download_info:
                export_clicked = False
                for selector in export_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.count() > 0:
                            element.click(timeout=5000)
                            print(f"✅ Export 버튼 클릭: {selector}")
                            export_clicked = True
                            break
                    except:
                        continue

                if not export_clicked:
                    print("❌ Export 버튼을 찾을 수 없습니다")
                    debug_ss = PROJECT_ROOT / 'temp' / 'no_export.png'
                    page.screenshot(path=str(debug_ss), full_page=True)
                    print(f"   스크린샷: {debug_ss}")
                    raise Exception("Export 버튼 없음")

            # 다운로드 완료 대기
            download = download_info.value
            print("⏳ 다운로드 중...")

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

            # 에러 스크린샷
            try:
                error_ss = PROJECT_ROOT / 'temp' / 'export_error.png'
                page.screenshot(path=str(error_ss), full_page=True)
                print(f"📸 에러 스크린샷: {error_ss}")
            except:
                pass

            downloaded_file = None

        finally:
            browser.close()

    return downloaded_file


def main():
    """메인 함수"""
    print("=" * 60)
    print("Desktop Claude Export (수동 Cloudflare 해결)")
    print(f"모드: {'NAS 직접 저장' if USE_NAS else '로컬 저장'}")
    print("=" * 60)
    print()

    if not ensure_export_dir():
        return

    result_file = auto_export_manual()

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
        else:
            print()
            print("다음 단계:")
            print(f"  scp {result_file} pi:~/learning-etl/temp/")
    else:
        print()
        print("❌ Export 실패")


if __name__ == '__main__':
    main()
