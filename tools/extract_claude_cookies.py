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
import base64
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

        # Chrome v80+ AES 암호화 키 로드
        self.encryption_key = None
        if sys.platform == 'win32':
            self.encryption_key = self.get_encryption_key()
            if self.encryption_key:
                print(f"✅ 암호화 키 로드 성공")
            else:
                print(f"⚠️  암호화 키 로드 실패 - DPAPI 방식으로 시도")

    def find_chrome_cookies(self):
        """Chrome/Edge 쿠키 DB 경로 찾기 (모든 프로필 검색)"""
        possible_paths = []

        if sys.platform == 'win32':
            localappdata = Path(os.environ.get('LOCALAPPDATA', ''))

            # Chrome 프로필 검색
            chrome_base = localappdata / 'Google/Chrome/User Data'
            if chrome_base.exists():
                # Default 프로필
                for cookie_path in [
                    chrome_base / 'Default/Network/Cookies',
                    chrome_base / 'Default/Cookies'
                ]:
                    if cookie_path.exists():
                        possible_paths.append(cookie_path)

                # 다른 프로필들 (Profile 1, Profile 2, etc.)
                for profile_dir in chrome_base.glob('Profile *'):
                    for cookie_path in [
                        profile_dir / 'Network/Cookies',
                        profile_dir / 'Cookies'
                    ]:
                        if cookie_path.exists():
                            possible_paths.append(cookie_path)

            # Edge 프로필
            edge_base = localappdata / 'Microsoft/Edge/User Data'
            if edge_base.exists():
                for cookie_path in [
                    edge_base / 'Default/Network/Cookies',
                    edge_base / 'Default/Cookies'
                ]:
                    if cookie_path.exists():
                        possible_paths.append(cookie_path)

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

        # 각 프로필에서 claude.ai 쿠키 찾기
        for path in possible_paths:
            if path.exists():
                # 임시로 쿠키 확인
                temp_db = Path(__file__).parent / 'temp_cookies_check.db'
                try:
                    shutil.copy2(path, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM cookies WHERE host_key LIKE ?",
                        ('%claude.ai%',)
                    )
                    count = cursor.fetchone()[0]
                    conn.close()
                    temp_db.unlink()

                    if count > 0:
                        print(f"✅ 쿠키 DB 발견: {path} ({count}개 Claude 쿠키)")
                        return path
                except:
                    if temp_db.exists():
                        temp_db.unlink()
                    continue

        # Claude 쿠키가 없으면 첫 번째 발견된 DB 반환
        for path in possible_paths:
            if path.exists():
                print(f"⚠️  쿠키 DB 발견: {path} (Claude 쿠키 없음)")
                return path

        return None

    def get_encryption_key(self):
        """Chrome/Edge의 AES 암호화 키 가져오기 (Windows)"""
        try:
            # 쿠키 DB 경로에서 User Data 경로 추출
            user_data_path = self.cookie_db_path
            while user_data_path.name != 'User Data':
                user_data_path = user_data_path.parent
                if user_data_path == user_data_path.parent:
                    return None

            local_state_path = user_data_path / 'Local State'
            if not local_state_path.exists():
                return None

            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)

            encrypted_key = local_state['os_crypt']['encrypted_key']
            encrypted_key = base64.b64decode(encrypted_key)

            # DPAPI로 암호화된 키 복호화 (DPAPI 프리픽스 제거)
            encrypted_key = encrypted_key[5:]  # "DPAPI" 프리픽스 제거
            decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

            return decrypted_key

        except Exception as e:
            print(f"⚠️  암호화 키 로드 실패: {e}")
            return None

    def decrypt_windows_cookie(self, encrypted_value):
        """Windows에서 Chrome 쿠키 복호화 (v80+ AES-GCM 지원)"""
        try:
            # Chrome v80+ 는 AES-GCM 암호화 사용 (v10, v11, v20 등)
            prefix = encrypted_value[:3]

            if prefix.startswith(b'v1') or prefix.startswith(b'v2'):
                if not self.encryption_key:
                    return None

                # AES-GCM 복호화
                from Crypto.Cipher import AES

                # v10/v11 프리픽스 제거
                encrypted_value = encrypted_value[3:]

                # Nonce (12 bytes) + Ciphertext + Tag (16 bytes)
                nonce = encrypted_value[:12]
                ciphertext_and_tag = encrypted_value[12:]

                # Tag는 마지막 16 bytes
                ciphertext = ciphertext_and_tag[:-16]
                tag = ciphertext_and_tag[-16:]

                cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
                decrypted = cipher.decrypt_and_verify(ciphertext, tag)

                return decrypted.decode('utf-8')
            else:
                # DPAPI 암호화 (이전 버전)
                return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
        except Exception as e:
            # 복호화 실패는 정상 (일부 쿠키는 빈 값일 수 있음)
            print(f"    [DECRYPT ERROR] {type(e).__name__}: {e}")
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

        # Chrome/Edge가 실행 중이면 파일이 잠겨있을 수 있음
        # 여러 방법 시도
        try:
            shutil.copy2(self.cookie_db_path, temp_db)
        except PermissionError:
            # Windows: 읽기 모드로 열어서 복사
            try:
                with open(self.cookie_db_path, 'rb') as src:
                    with open(temp_db, 'wb') as dst:
                        dst.write(src.read())
            except Exception as e:
                raise PermissionError(
                    f"쿠키 DB를 읽을 수 없습니다.\n"
                    f"Chrome/Edge를 종료하고 다시 시도하거나,\n"
                    f"또는 브라우저의 '작업 관리자'에서 모든 Chrome/Edge 프로세스를 종료하세요.\n"
                    f"원본 에러: {e}"
                )

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
                    print(f"  ⚠️  쿠키 복호화 실패: {name}")
                    continue
                else:
                    print(f"  ✅ {name}: {value[:20]}...")

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
