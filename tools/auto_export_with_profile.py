#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desktop Claude Export (Chrome Profile 사용)

쿠키 JSON 대신 Chrome 사용자 프로필을 직접 사용하여
Cloudflare가 신뢰하는 세션으로 Export 수행

실행:
  python tools/auto_export_with_profile.py
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

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 설정
USE_NAS = True  # True: NAS 직접 저장, False: 로컬 저장

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
        if USE_NAS:
            print("NAS(Z:)가 마운트되어 있는지 확인하세요.")
        return False


def auto_export_with_profile(headless=False):
    """Chrome 프로필 사용하여 Export

    Args:
        headless: True면 백그라운드 실행 (Cloudflare 우회 어려움)

    Returns:
        다운로드된 파일 경로 또는 None
    """
    print("=" * 60)
    print("Claude.ai Export (Chrome Profile)")
    print("=" * 60)
    print()

    # Chrome 프로필 경로
    localappdata = Path(os.environ['LOCALAPPDATA'])
    chrome_user_data = localappdata / 'Google/Chrome/User Data'

    if not chrome_user_data.exists():
        print(f"❌ Chrome 프로필을 찾을 수 없습니다: {chrome_user_data}")
        print("Chrome이 설치되어 있는지 확인하세요.")
        return None

    # 사용 중인 프로필 찾기
    available_profiles = []
    for profile_dir in chrome_user_data.iterdir():
        if profile_dir.is_dir() and (profile_dir.name.startswith('Profile') or profile_dir.name == 'Default'):
            cookie_file = profile_dir / 'Network' / 'Cookies'
            if cookie_file.exists():
                available_profiles.append(profile_dir.name)

    if not available_profiles:
        print("❌ Chrome 프로필에서 쿠키를 찾을 수 없습니다.")
        return None

    print(f"✅ 사용 가능한 프로필: {', '.join(available_profiles)}")
    print(f"   사용할 프로필: {available_profiles[0]}")
    print()

    with sync_playwright() as p:
        print("🌐 Chrome 프로필로 브라우저 실행...")
        print("   (Cloudflare가 실제 브라우저로 인식)")
        print()

        try:
            # Chrome 프로필을 직접 사용
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(chrome_user_data),
                headless=False,  # headless=True면 Cloudflare 감지
                channel='chrome',
                downloads_path=str(DOWNLOADS_DIR),
                args=[
                    f'--profile-directory={available_profiles[0]}',
                ]
            )

            page = context.pages[0] if context.pages else context.new_page()

            # 1. claude.ai 접속
            print("📡 claude.ai 접속...")
            page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)

            # 2. Settings 페이지로 이동
            print("⚙️  Settings 페이지 이동...")
            try:
                page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                # challenge_redirect 발생 시 재시도
                if 'challenge_redirect' in str(e) or '/new' in page.url:
                    print("   리다이렉트 감지 - Settings 재시도...")
                    time.sleep(3)
                    page.goto("https://claude.ai/settings", wait_until='domcontentloaded', timeout=60000)
                else:
                    raise
            time.sleep(5)

            # Cloudflare 체크
            page_text = page.inner_text('body')
            if '사람인지 확인' in page_text or ('Cloudflare' in page_text and len(page_text) < 500):
                print()
                print("=" * 60)
                print("⚠️  Cloudflare 챌린지 감지")
                print("=" * 60)
                print("브라우저 창에서 '사람인지 확인' 체크박스를 클릭하세요.")
                print("완료되면 자동으로 다음 단계로 진행됩니다...")
                print()

                # 사용자가 체크박스 클릭할 때까지 대기
                page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        return !text.includes('사람인지 확인') &&
                               !text.includes('Cloudflare') &&
                               text.length > 500;
                    }""",
                    timeout=300000  # 5분
                )
                print("✅ Cloudflare 통과")
                time.sleep(2)

            # 3. Privacy 탭 찾기
            print("🔐 Privacy 탭 찾기...")
            privacy_selectors = [
                "a:has-text('Privacy')",
                "a:has-text('개인정보')",
                "a[href*='privacy']",
            ]

            privacy_clicked = False
            for selector in privacy_selectors:
                try:
                    privacy_link = page.locator(selector).first
                    if privacy_link.count() > 0:
                        privacy_link.click(timeout=5000)
                        time.sleep(2)
                        print(f"✅ Privacy 탭 클릭: {selector}")
                        privacy_clicked = True
                        break
                except:
                    continue

            if not privacy_clicked:
                # 페이지 텍스트 확인
                current_text = page.inner_text('body')
                if 'Privacy' in current_text or '개인정보' in current_text:
                    print("✅ Privacy 섹션으로 이동한 것으로 보임")
                else:
                    debug_ss = PROJECT_ROOT / 'temp' / 'settings_debug.png'
                    page.screenshot(path=str(debug_ss), full_page=True)
                    print(f"⚠️  Privacy 탭을 찾을 수 없습니다.")
                    print(f"   스크린샷: {debug_ss}")
                    raise Exception("Privacy 탭을 찾을 수 없습니다")

            # 4. Export 버튼 클릭
            print("💾 Export 버튼 찾기...")
            export_selectors = [
                "button:has-text('Export data')",
                "button:has-text('Export')",
                "button:has-text('내보내기')",
                "button:has-text('데이터 내보내기')",
            ]

            downloaded_file = None

            # 다운로드 대기 설정
            with page.expect_download(timeout=180000) as download_info:
                export_clicked = False
                for selector in export_selectors:
                    try:
                        export_btn = page.locator(selector).first
                        if export_btn.count() > 0:
                            export_btn.click(timeout=5000)
                            print(f"✅ Export 버튼 클릭: {selector}")
                            export_clicked = True
                            break
                    except:
                        continue

                if not export_clicked:
                    print("⚠️  Export 버튼을 찾을 수 없습니다.")
                    raise Exception("Export 버튼을 찾을 수 없습니다")

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
            downloaded_file = None

        finally:
            context.close()

    return downloaded_file


def main():
    """메인 함수"""
    print("=" * 60)
    print("Desktop Claude Export (Chrome Profile)")
    print(f"모드: {'NAS 직접 저장' if USE_NAS else '로컬 저장 후 전송'}")
    print("=" * 60)
    print()

    # Export 디렉토리 확인
    if not ensure_export_dir():
        return

    # Chrome이 실행 중이면 경고
    import psutil
    chrome_running = any(p.info['name'] == 'chrome.exe' for p in psutil.process_iter(['name']))
    if chrome_running:
        print("⚠️  Chrome이 실행 중입니다.")
        print("   Playwright가 별도 프로필을 사용하므로 계속 진행합니다...")
        print()

    # Export 실행
    result_file = auto_export_with_profile(headless=False)

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
    main()
