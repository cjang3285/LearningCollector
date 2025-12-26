#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright를 사용하여 Claude.ai 쿠키를 자동으로 추출

이 방법은 Chrome의 암호화된 쿠키 DB를 복호화하지 않고,
실제 브라우저를 실행하여 쿠키를 가져옵니다.

사용법:
  python tools/extract_cookies_playwright.py
  python tools/extract_cookies_playwright.py --upload
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import argparse

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright가 설치되지 않았습니다.")
    print("   설치: pip install playwright")
    print("   브라우저 설치: playwright install chromium")
    sys.exit(1)


class PlaywrightCookieExtractor:
    """Playwright를 사용한 쿠키 추출기"""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def extract_cookies(self, domain='claude.ai'):
        """브라우저를 실행하여 쿠키 추출"""
        print(f"🌐 브라우저 시작 중...")

        try:
            self.playwright = sync_playwright().start()

            # 사용자의 Chrome 프로필 경로 찾기
            chrome_user_data = self.find_chrome_profile()

            if chrome_user_data:
                print(f"✅ Chrome 프로필 발견: {chrome_user_data}")
                # 기존 Chrome 프로필 사용
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(chrome_user_data),
                    headless=False,
                    channel='chrome',  # 시스템에 설치된 Chrome 사용
                    args=['--disable-blink-features=AutomationControlled']
                )
                self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            else:
                print("⚠️  Chrome 프로필을 찾을 수 없습니다. 새 브라우저로 시작합니다.")
                self.browser = self.playwright.chromium.launch(headless=False)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()

            # Claude.ai로 이동 (이미 프로필에 쿠키가 있으면 바로 가져올 수 있음)
            print(f"🔄 {domain}로 이동 중...")
            try:
                self.page.goto(f"https://{domain}", wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                print(f"⚠️  페이지 로드 타임아웃 (무시하고 진행): {e}")

            # 쿠키 추출 (페이지 로드 여부와 관계없이 프로필의 쿠키 사용)
            cookies = self.context.cookies(f"https://{domain}")

            # Claude.ai 도메인 필터링
            claude_cookies = [
                c for c in cookies
                if domain in c.get('domain', '')
            ]

            if not claude_cookies:
                print(f"❌ {domain} 쿠키를 찾을 수 없습니다.")
                print(f"   브라우저에서 {domain}에 로그인되어 있는지 확인하세요.")
                return []

            print(f"✅ {len(claude_cookies)}개 쿠키 추출 완료")

            # Playwright 쿠키 형식을 표준 형식으로 변환
            formatted_cookies = []
            for c in claude_cookies:
                formatted_cookies.append({
                    'name': c['name'],
                    'value': c['value'],
                    'domain': c['domain'],
                    'path': c['path'],
                    'secure': c.get('secure', True),
                    'httpOnly': c.get('httpOnly', False),
                    'sameSite': c.get('sameSite', 'Lax')
                })

            return formatted_cookies

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            import traceback
            traceback.print_exc()
            return []

        finally:
            self.close()

    def find_chrome_profile(self):
        """Chrome 프로필 경로 찾기"""
        if sys.platform == 'win32':
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data'
            # Profile 1이 주로 사용되는 프로필
            profiles = ['Profile 1', 'Default', 'Profile 2']
            for profile in profiles:
                profile_path = base / profile
                if profile_path.exists():
                    return profile_path
        elif sys.platform == 'darwin':
            return Path.home() / 'Library/Application Support/Google/Chrome/Default'
        else:  # Linux
            return Path.home() / '.config/google-chrome/Default'

        return None

    def close(self):
        """브라우저 종료"""
        if self.context:
            try:
                self.context.close()
            except:
                pass
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass


def save_cookies(cookies, output_path):
    """쿠키를 JSON 파일로 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)

    print(f"✅ 쿠키 저장: {output_path}")


def upload_to_raspberry_pi(cookie_file, pi_user='jcw', pi_host='183.101.163.146'):
    """Raspberry Pi로 쿠키 파일 업로드"""
    remote_path = f"{pi_user}@{pi_host}:~/learning-etl/temp/claude_cookies.json"

    print(f"\n🚀 Raspberry Pi로 업로드 중...")
    print(f"   대상: {remote_path}")

    try:
        result = subprocess.run(
            ['scp', str(cookie_file), remote_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"✅ 업로드 성공!")
            return True
        else:
            print(f"❌ 업로드 실패: {result.stderr}")
            return False

    except FileNotFoundError:
        print("❌ scp 명령어를 찾을 수 없습니다. OpenSSH를 설치하세요.")
        return False
    except Exception as e:
        print(f"❌ 업로드 중 에러: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Claude.ai 쿠키 자동 추출 (Playwright)')
    parser.add_argument('--upload', action='store_true', help='Raspberry Pi로 자동 업로드')
    parser.add_argument('--output', default='temp/claude_cookies.json', help='출력 파일 경로')
    parser.add_argument('--pi-user', default='jcw', help='Raspberry Pi 사용자명')
    parser.add_argument('--pi-host', default='183.101.163.146', help='Raspberry Pi 호스트')
    args = parser.parse_args()

    print("=" * 60)
    print("Claude.ai 쿠키 자동 추출 도구 (Playwright)")
    print("=" * 60)
    print()

    try:
        # 쿠키 추출
        extractor = PlaywrightCookieExtractor()
        cookies = extractor.extract_cookies('claude.ai')

        if not cookies:
            print("\n❌ 쿠키 추출 실패")
            sys.exit(1)

        # 로컬 저장
        output_path = Path(__file__).parent.parent / args.output
        output_path = output_path.resolve()
        save_cookies(cookies, output_path)

        # Raspberry Pi 업로드
        if args.upload:
            upload_to_raspberry_pi(output_path, args.pi_user, args.pi_host)

        print("\n" + "=" * 60)
        print("✅ 완료!")
        print("=" * 60)

        if not args.upload:
            print(f"\n💡 Raspberry Pi로 업로드하려면:")
            print(f"   python {__file__} --upload")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
