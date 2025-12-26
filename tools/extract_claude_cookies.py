#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬 Chrome/Edge 프로필에서 Claude.ai 쿠키를 자동으로 추출하여
Raspberry Pi로 업로드하는 스크립트

사용법:
  python tools/extract_claude_cookies.py
  python tools/extract_claude_cookies.py --upload  # 자동 업로드
"""

import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import argparse

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 크로스 플랫폼 암호화 라이브러리 임포트
try:
    if sys.platform == 'win32':
        import win32crypt
    elif sys.platform == 'darwin':
        import keyring
        from Crypto.Cipher import AES
        from Crypto.Protocol.KDF import PBKDF2
    else:  # Linux
        from Crypto.Cipher import AES
        from Crypto.Protocol.KDF import PBKDF2
except ImportError as e:
    print(f"⚠️  필요한 라이브러리 설치: pip install pywin32 pycryptodome")
    sys.exit(1)


class ChromeCookieExtractor:
    """Chrome/Edge 쿠키 추출기"""

    def __init__(self):
        self.cookie_db_path = self.find_chrome_cookies()
        if not self.cookie_db_path:
            raise FileNotFoundError("Chrome/Edge 쿠키 DB를 찾을 수 없습니다")

    def find_chrome_cookies(self):
        """Chrome/Edge 쿠키 DB 경로 찾기"""
        if sys.platform == 'win32':
            possible_paths = [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data/Default/Network/Cookies',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data/Default/Cookies',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Edge/User Data/Default/Network/Cookies',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Edge/User Data/Default/Cookies',
            ]
        elif sys.platform == 'darwin':  # macOS
            home = Path.home()
            possible_paths = [
                home / 'Library/Application Support/Google/Chrome/Default/Cookies',
                home / 'Library/Application Support/Microsoft Edge/Default/Cookies',
            ]
        else:  # Linux
            home = Path.home()
            possible_paths = [
                home / '.config/google-chrome/Default/Cookies',
                home / '.config/chromium/Default/Cookies',
            ]

        for path in possible_paths:
            if path.exists():
                print(f"✅ 쿠키 DB 발견: {path}")
                return path

        return None

    def decrypt_windows_cookie(self, encrypted_value):
        """Windows DPAPI로 암호화된 쿠키 복호화"""
        try:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()
        except:
            return None

    def decrypt_mac_cookie(self, encrypted_value):
        """macOS Keychain으로 암호화된 쿠키 복호화"""
        try:
            # Chrome Safe Storage 키 가져오기
            password = keyring.get_password('Chrome Safe Storage', 'Chrome')
            if not password:
                return None

            # AES 복호화
            salt = b'saltysalt'
            iv = b' ' * 16
            key = PBKDF2(password, salt, dkLen=16, count=1003)
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)

            decrypted = cipher.decrypt(encrypted_value[3:])
            return decrypted[:-decrypted[-1]].decode()
        except:
            return None

    def extract_cookies(self, domain='claude.ai'):
        """특정 도메인의 쿠키 추출"""
        # 쿠키 DB 임시 복사 (잠금 방지)
        temp_db = Path(__file__).parent / 'temp_cookies.db'
        shutil.copy2(self.cookie_db_path, temp_db)

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # 쿠키 조회
            cursor.execute(
                "SELECT name, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly, samesite "
                "FROM cookies WHERE host_key LIKE ?",
                (f'%{domain}%',)
            )

            cookies = []
            for row in cursor.fetchall():
                name, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly, samesite = row

                # 쿠키 값 복호화
                if sys.platform == 'win32':
                    value = self.decrypt_windows_cookie(encrypted_value)
                elif sys.platform == 'darwin':
                    value = self.decrypt_mac_cookie(encrypted_value)
                else:  # Linux (암호화 안됨)
                    value = encrypted_value.decode() if encrypted_value else ''

                if not value:
                    continue

                # SameSite 값 변환
                samesite_map = {0: 'None', 1: 'Lax', 2: 'Strict'}
                samesite_str = samesite_map.get(samesite, 'Lax')

                cookie = {
                    'name': name,
                    'value': value,
                    'domain': host_key,
                    'path': path,
                    'secure': bool(is_secure),
                    'httpOnly': bool(is_httponly),
                    'sameSite': samesite_str
                }
                cookies.append(cookie)

            conn.close()
            return cookies

        finally:
            # 임시 파일 삭제
            if temp_db.exists():
                temp_db.unlink()

    def save_cookies(self, cookies, output_path):
        """쿠키를 JSON 파일로 저장"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"✅ 쿠키 저장: {output_path}")
        print(f"   총 {len(cookies)}개 쿠키 추출")


def upload_to_raspberry_pi(cookie_file, pi_user='jcw', pi_host='183.101.163.146'):
    """Raspberry Pi로 쿠키 파일 업로드"""
    import subprocess

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
        else:
            print(f"❌ 업로드 실패: {result.stderr}")
            return False

        return True

    except FileNotFoundError:
        print("❌ scp 명령어를 찾을 수 없습니다. OpenSSH를 설치하세요.")
        return False
    except Exception as e:
        print(f"❌ 업로드 중 에러: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Claude.ai 쿠키 자동 추출')
    parser.add_argument('--upload', action='store_true', help='Raspberry Pi로 자동 업로드')
    parser.add_argument('--output', default='temp/claude_cookies.json', help='출력 파일 경로')
    parser.add_argument('--pi-user', default='jcw', help='Raspberry Pi 사용자명')
    parser.add_argument('--pi-host', default='183.101.163.146', help='Raspberry Pi 호스트')
    args = parser.parse_args()

    print("=" * 60)
    print("Claude.ai 쿠키 자동 추출 도구")
    print("=" * 60)

    try:
        # 쿠키 추출
        extractor = ChromeCookieExtractor()
        cookies = extractor.extract_cookies('claude.ai')

        if not cookies:
            print("❌ claude.ai 쿠키를 찾을 수 없습니다.")
            print("   Chrome/Edge에서 claude.ai에 로그인되어 있는지 확인하세요.")
            sys.exit(1)

        # 로컬 저장
        output_path = Path(__file__).parent.parent / args.output
        output_path = output_path.resolve()  # 절대 경로로 변환
        extractor.save_cookies(cookies, output_path)

        # Raspberry Pi 업로드
        if args.upload:
            upload_to_raspberry_pi(output_path, args.pi_user, args.pi_host)

        print("\n" + "=" * 60)
        print("✅ 완료!")
        print("=" * 60)

        if not args.upload:
            print(f"\n💡 Raspberry Pi로 업로드하려면:")
            print(f"   python {__file__} --upload")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
